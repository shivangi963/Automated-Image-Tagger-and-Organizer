from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from app.models import ImageResponse, ImageTag, ImageUpdate, PresignRequest
from app.auth import get_current_user, get_user_id
from app.database import get_database
from app.storage import storage
from app.config import settings
from app.tasks.image_processing import process_image
from datetime import datetime, timedelta
from bson import ObjectId
import logging

router = APIRouter(prefix="/images", tags=["Images"])
logger = logging.getLogger(__name__)


def _make_image_dict(img: dict) -> dict:
    """
    Build a complete image dict with presigned URLs embedded.
    Calling this once per image eliminates N+1 URL requests from the frontend.
    """
    img_id = str(img["_id"])
    storage_key = img.get("storage_key", "")
    thumbnail_key = img.get("thumbnail_key")

    # Generate presigned URLs (sync, fast)
    url = storage.get_presigned_url(storage_key) if storage_key else None
    thumbnail_url = storage.get_presigned_url(thumbnail_key) if thumbnail_key else url

    # Normalize tags — handle both dict and string formats
    raw_tags = img.get("tags", [])
    tags = []
    for tag in raw_tags:
        if isinstance(tag, dict):
            tags.append({
                "tag_name": tag.get("tag_name") or tag.get("label") or tag.get("name", ""),
                "confidence": tag.get("confidence", 1.0),
                "source": tag.get("source", "yolo"),
            })
        elif isinstance(tag, str):
            tags.append({"tag_name": tag, "confidence": 1.0, "source": "user"})

    return {
        "_id": img_id,
        "id": img_id,
        "user_id": str(img.get("user_id", "")),
        "storage_key": storage_key,
        "filename": img.get("filename") or img.get("original_filename", ""),
        "original_filename": img.get("original_filename", ""),
        "mime_type": img.get("mime_type", ""),
        "metadata": img.get("metadata"),
        "phash": img.get("phash"),
        "tags": tags,
        "tag_strings": img.get("tag_strings", [t["tag_name"].lower() for t in tags]),
        "status": img.get("status", "pending"),
        "created_at": img.get("created_at"),
        "processed_at": img.get("processed_at"),
        # ✅ URLs embedded — frontend needs zero extra requests
        "url": url,
        "thumbnailUrl": thumbnail_url,
    }


@router.get("/", response_model=List[dict])
async def list_images(
    current_user: dict = Depends(get_current_user),
    db=Depends(get_database),
):
    """
    List all images for current user with presigned URLs embedded.
    Single DB query + one presigned URL per image = no N+1 problem.
    """
    try:
        user_id = str(current_user["_id"])
        images = (
            await db.images.find({"user_id": user_id})
            .sort("created_at", -1)
            .to_list(None)
        )
        result = [_make_image_dict(img) for img in images]
        logger.info(f"Listed {len(result)} images for user {user_id}")
        return result
    except Exception as e:
        logger.exception(f"Error listing images: {e}")
        raise HTTPException(status_code=500, detail="Failed to list images")


@router.get("/{image_id}", response_model=dict)
async def get_image(
    image_id: str,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_database),
):
    """Get single image with embedded URL."""
    user_id = get_user_id(current_user)
    image = await db.images.find_one({"_id": ObjectId(image_id), "user_id": user_id})
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")
    return _make_image_dict(image)


@router.get("/{image_id}/url")
async def get_image_url(
    image_id: str,
    thumbnail: bool = False,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_database),
):
    """
    Backwards-compatible endpoint — still works but frontend
    should prefer the embedded URLs from list/get endpoints.
    """
    user_id = get_user_id(current_user)
    image = await db.images.find_one({"_id": ObjectId(image_id), "user_id": user_id})
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")

    key = (
        image.get("thumbnail_key")
        if thumbnail and image.get("thumbnail_key")
        else image["storage_key"]
    )
    url = storage.get_presigned_url(key)
    if not url:
        raise HTTPException(status_code=500, detail="Failed to generate URL")
    return {"url": url}


@router.delete("/{image_id}")
async def delete_image(
    image_id: str,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_database),
):
    """Delete an image from storage and database."""
    user_id = get_user_id(current_user)
    image = await db.images.find_one({"_id": ObjectId(image_id), "user_id": user_id})
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")

    storage.delete_file(image["storage_key"])
    if image.get("thumbnail_key"):
        storage.delete_file(image["thumbnail_key"])

    await db.images.delete_one({"_id": ObjectId(image_id)})
    return {"message": "Image deleted successfully"}


@router.post("/presign", response_model=dict)
async def presign_upload(
    request: PresignRequest,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_database),
):
    """Generate presigned PUT URL for direct MinIO upload."""
    try:
        user_id = get_user_id(current_user)

        if not storage or not storage.client:
            raise HTTPException(status_code=500, detail="Storage service unavailable")

        key = storage.generate_key(user_id, request.filename)
        presigned_url = storage.client.get_presigned_url(
            "PUT",
            settings.MINIO_BUCKET,
            key,
            expires=timedelta(hours=1),
        )

        logger.info(f"Generated presigned URL for {key}")
        return {"url": presigned_url, "storageKey": key}

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error generating presigned URL: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate presigned URL: {str(e)}")


class IngestRequest(BaseModel):
    filename: str
    mime_type: str
    storage_key: str


@router.post("/ingest", response_model=dict)
async def ingest_image(
    request: IngestRequest,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_database),
):
    """Register an already-uploaded MinIO object and queue AI processing."""
    try:
        user_id = str(current_user["_id"])

        image_doc = {
            "user_id": user_id,
            "filename": request.filename,
            "original_filename": request.filename,
            "mime_type": request.mime_type,
            "storage_key": request.storage_key,
            "status": "pending",
            "tags": [],
            "tag_strings": [],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }

        result = await db.images.insert_one(image_doc)
        image_id = str(result.inserted_id)

        try:
            task = process_image.delay(image_id)
            logger.info(f"Celery task {task.id} queued for image {image_id}")
        except Exception as e:
            logger.error(f"Failed to queue Celery task: {e}")

        return {"id": image_id, "status": "pending", "message": "Image queued for AI processing"}

    except Exception as e:
        logger.exception(f"Error ingesting image: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to ingest image: {str(e)}")


@router.post("/upload", response_model=List[dict])
async def upload_images(
    files: List[UploadFile] = File(...),
    current_user: dict = Depends(get_current_user),
    db=Depends(get_database),
):
    """Upload one or more images directly (multipart/form-data)."""
    user_id = get_user_id(current_user)
    uploaded = []

    for file in files:
        try:
            content = await file.read()
            storage_key = storage.generate_key(user_id, file.filename)

            if not storage.upload_file(content, storage_key, file.content_type):
                logger.error(f"Storage upload failed for {file.filename}")
                continue

            image_doc = {
                "user_id": user_id,
                "filename": file.filename,
                "original_filename": file.filename,
                "mime_type": file.content_type,
                "storage_key": storage_key,
                "status": "pending",
                "tags": [],
                "tag_strings": [],
                "created_at": datetime.utcnow(),
            }

            result = await db.images.insert_one(image_doc)
            image_id = str(result.inserted_id)
            process_image.delay(image_id)

            # Return with URL so the UI can show it immediately
            url = storage.get_presigned_url(storage_key)
            uploaded.append({
                **image_doc,
                "_id": image_id,
                "id": image_id,
                "url": url,
                "thumbnailUrl": url,
            })

        except Exception as e:
            logger.error(f"Error uploading {file.filename}: {e}")

    return uploaded