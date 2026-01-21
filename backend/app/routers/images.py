from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from app.models import ImageResponse, ImageTag, ImageUpdate, PresignRequest
from app.auth import get_current_user, get_user_id
from app.database import get_database
from app.storage import storage
from app.config import settings
from app.tasks.image_processing import process_image  # ✅ FIXED - removed process_image_sync
from datetime import datetime, timedelta
from bson import ObjectId
import logging
import asyncio

router = APIRouter(prefix="/images", tags=["Images"])
logger = logging.getLogger(__name__)


@router.post("/upload", response_model=List[ImageResponse])
async def upload_images(
    files: List[UploadFile] = File(...),
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    """Upload one or more images"""
    user_id = get_user_id(current_user)
    uploaded_images = []
    
    for file in files:
        try:
            # Read file content
            content = await file.read()
            
            # Generate storage key
            storage_key = storage.generate_key(user_id, file.filename)
            
            # Upload to MinIO
            success = storage.upload_file(content, storage_key, file.content_type)
            if not success:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to upload {file.filename}"
                )
            
            # Create image document
            image_doc = {
                "user_id": user_id,
                "storage_key": storage_key,
                "original_filename": file.filename,
                "mime_type": file.content_type,
                "status": "pending",
                "created_at": datetime.utcnow()
            }
            
            result = await db.images.insert_one(image_doc)
            image_id = str(result.inserted_id)
            
            # Queue processing task
            process_image.delay(image_id)
            
            uploaded_images.append(ImageResponse(
                id=image_id,
                user_id=user_id,
                storage_key=storage_key,
                original_filename=file.filename,
                mime_type=file.content_type,
                metadata=None,
                phash=None,
                tags=[],
                status="pending",
                created_at=image_doc["created_at"]
            ))
            
        except Exception as e:
            logger.error(f"Error uploading {file.filename}: {e}")
            continue
    
    return uploaded_images


@router.get("/", response_model=List[dict])
async def list_images(
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    """List all images for current user"""
    try:
        user_id = str(current_user["_id"])
        images = await db.images.find({"user_id": user_id}).sort("created_at", -1).to_list(None)
        
        # Convert ObjectId to string and ensure tags are included
        for img in images:
            img["_id"] = str(img["_id"])
            img["id"] = img["_id"]
            
            # Ensure tags field exists (might be missing for old images)
            if "tags" not in img:
                img["tags"] = []
            
            # Ensure tag_strings exists for search
            if "tag_strings" not in img:
                img["tag_strings"] = [tag.get("tag_name", "").lower() for tag in img.get("tags", [])]
        
        logger.info(f"Listed {len(images)} images for user {user_id}")
        return images
        
    except Exception as e:
        logger.exception(f"Error listing images: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list images"
        )


@router.get("/{image_id}", response_model=ImageResponse)
async def get_image(
    image_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    """Get image details"""
    user_id = get_user_id(current_user)
    
    image = await db.images.find_one({"_id": ObjectId(image_id), "user_id": user_id})
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")
    
    # Tags are stored directly in image document
    tags = image.get("tags", [])
    
    return ImageResponse(
        id=str(image["_id"]),
        user_id=image["user_id"],
        storage_key=image["storage_key"],
        original_filename=image["original_filename"],
        mime_type=image["mime_type"],
        metadata=image.get("metadata"),
        phash=image.get("phash"),
        tags=tags,
        status=image["status"],
        created_at=image["created_at"],
        processed_at=image.get("processed_at"),
        thumbnailUrl=None
    )


@router.get("/{image_id}/url")
async def get_image_url(
    image_id: str,
    thumbnail: bool = False,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    """Get presigned URL for image"""
    user_id = get_user_id(current_user)
    
    image = await db.images.find_one({"_id": ObjectId(image_id), "user_id": user_id})
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")
    
    key = image.get("thumbnail_key") if thumbnail and image.get("thumbnail_key") else image["storage_key"]
    url = storage.get_presigned_url(key)
    
    if not url:
        raise HTTPException(status_code=500, detail="Failed to generate URL")
    
    return {"url": url}


@router.delete("/{image_id}")
async def delete_image(
    image_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    """Delete an image"""
    user_id = get_user_id(current_user)
    
    image = await db.images.find_one({"_id": ObjectId(image_id), "user_id": user_id})
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")
    
    # Delete from storage
    storage.delete_file(image["storage_key"])
    if image.get("thumbnail_key"):
        storage.delete_file(image["thumbnail_key"])
    
    # Delete from database
    await db.images.delete_one({"_id": ObjectId(image_id)})
    
    return {"message": "Image deleted successfully"}


@router.post("/presign", response_model=dict)
async def presign_upload(
    request: PresignRequest,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    """Generate presigned URL for direct MinIO upload"""
    try:
        user_id = get_user_id(current_user)
        logger.info(f"Presign request: user_id={user_id}, filename={request.filename}, mime={request.mime}")
        
        # Verify storage is connected
        if not storage or not storage.client:
            logger.error("MinIO storage not initialized")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Storage service unavailable"
            )
        
        # Generate storage key
        key = storage.generate_key(user_id, request.filename)
        logger.info(f"Generated storage key: {key}")
        
        # Get presigned PUT URL (for uploading)
        presigned_url = storage.client.get_presigned_url(
            'PUT',
            settings.MINIO_BUCKET,
            key,
            expires=timedelta(hours=1)
        )
        
        logger.info(f"Generated presigned URL for {key}")
        
        return {
            "url": presigned_url,
            "storageKey": key
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error generating presigned URL: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate presigned URL: {str(e)}"
        )


class IngestRequest(BaseModel):
    """Schema for ingesting uploaded image"""
    filename: str
    mime_type: str
    storage_key: str

@router.post("/ingest", response_model=dict)
async def ingest_image(
    request: IngestRequest,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    """Ingest uploaded image from MinIO and create document in DB"""
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
        
        # ✅ Trigger Celery task to process the image
        try:
            task = process_image.delay(image_id)
            logger.info(f"Celery task {task.id} started for image {image_id}")
        except Exception as e:
            logger.error(f"Failed to start Celery task: {e}")
        
        return {
            "id": image_id,
            "status": "pending",
            "message": "Image uploaded, processing started"
        }
        
    except Exception as e:
        logger.exception(f"Error ingesting image: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to ingest image: {str(e)}"
        )


async def build_image_response(image_doc, db) -> Dict[str, Any]:
    """Helper to build ImageResponse with thumbnail URL"""
    image_id = str(image_doc["_id"])
    tags = image_doc.get("tags", [])
    
    # Generate thumbnail URL if available
    thumbnail_url = None
    if image_doc.get("thumbnail_key"):
        thumbnail_url = storage.get_presigned_url(image_doc["thumbnail_key"])
    
    # For now, also use original image as fallback
    if not thumbnail_url:
        thumbnail_url = storage.get_presigned_url(image_doc["storage_key"])
    
    response = ImageResponse(
        id=image_id,
        user_id=image_doc["user_id"],
        storage_key=image_doc["storage_key"],
        original_filename=image_doc["original_filename"],
        mime_type=image_doc["mime_type"],
        metadata=image_doc.get("metadata"),
        phash=image_doc.get("phash"),
        tags=tags,
        status=image_doc["status"],
        created_at=image_doc["created_at"],
        processed_at=image_doc.get("processed_at"),
        thumbnailUrl=None
    )
    
    # Add thumbnail URL to dict for frontend
    return {
        **response.dict(),
        "thumbnailUrl": thumbnail_url
    }