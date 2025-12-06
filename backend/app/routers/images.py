from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from app.models import ImageResponse, ImageTag, ImageUpdate, PresignRequest
from app.auth import get_current_user, get_user_id
from app.database import get_database
from app.storage import storage
from app.config import settings
from app.tasks.image_processing import process_image, process_image_sync  # Add this import
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
        
        # Convert ObjectId to string
        for img in images:
            img["_id"] = str(img["_id"])
            img["id"] = img["_id"]
        
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
    
    # Get tags
    tags = await get_image_tags(image_id, db)
    
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
        thumbnail_key=image.get("thumbnail_key")
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


@router.post("/{image_id}/tags")
async def add_custom_tag(
    image_id: str,
    tag_name: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    """Add custom tag to image"""
    user_id = get_user_id(current_user)
    
    # Verify image ownership
    image = await db.images.find_one({"_id": ObjectId(image_id), "user_id": user_id})
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")
    
    # Find or create tag
    tag = await db.tags.find_one({"name": tag_name.lower()})
    if not tag:
        result = await db.tags.insert_one({
            "name": tag_name.lower(),
            "source": "user",
            "created_at": datetime.utcnow()
        })
        tag_id = result.inserted_id
    else:
        tag_id = tag["_id"]
    
    # Create association
    await db.image_tags.update_one(
        {"image_id": ObjectId(image_id), "tag_id": tag_id},
        {
            "$set": {
                "confidence": 1.0,
                "source": "user",
                "created_at": datetime.utcnow()
            }
        },
        upsert=True
    )
    
    return {"message": "Tag added successfully"}


@router.delete("/{image_id}/tags/{tag_name}")
async def remove_tag(
    image_id: str,
    tag_name: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    """Remove tag from image"""
    user_id = get_user_id(current_user)
    
    # Verify ownership
    image = await db.images.find_one({"_id": ObjectId(image_id), "user_id": user_id})
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")
    
    # Find tag
    tag = await db.tags.find_one({"name": tag_name.lower()})
    if tag:
        await db.image_tags.delete_one({
            "image_id": ObjectId(image_id),
            "tag_id": tag["_id"]
        })
    
    return {"message": "Tag removed successfully"}


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
    await db.image_tags.delete_many({"image_id": ObjectId(image_id)})
    
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
        # expires must be a timedelta, not int
        presigned_url = storage.client.get_presigned_url(
            'PUT',
            settings.MINIO_BUCKET,
            key,
            expires=timedelta(hours=1)  # Changed from expires=3600
        )
        
        logger.info(f"Generated presigned URL for {key}: {presigned_url}")
        
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
            "status": "completed",  # ✅ Mark as completed immediately
            "tags": [],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
        
        result = await db.images.insert_one(image_doc)
        image_id = str(result.inserted_id)
        
        return {
            "id": image_id,
            "status": "completed"
        }
        
    except Exception as e:
        logger.exception(f"Error ingesting image: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to ingest image: {str(e)}"
        )


async def get_image_tags(image_id: str, db) -> List[ImageTag]:
    """Helper function to get tags for an image"""
    pipeline = [
        {"$match": {"image_id": ObjectId(image_id)}},
        {
            "$lookup": {
                "from": "tags",
                "localField": "tag_id",
                "foreignField": "_id",
                "as": "tag_info"
            }
        },
        {"$unwind": "$tag_info"}
    ]
    
    cursor = db.image_tags.aggregate(pipeline)
    tags = await cursor.to_list(length=100)
    
    return [
        ImageTag(
            tag_name=tag["tag_info"]["name"],
            confidence=tag.get("confidence", 1.0),
            source=tag.get("source", "unknown")
        )
        for tag in tags
    ]


async def build_image_response(image_doc, db) -> Dict[str, Any]:  # Changed return type
    """Helper to build ImageResponse with thumbnail URL"""
    image_id = str(image_doc["_id"])
    tags = await get_image_tags(image_id, db)
    
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
        thumbnail_key=image_doc.get("thumbnail_key")
    )
    
    # Add thumbnail URL to dict for frontend
    return {
        **response.dict(),
        "thumbnailUrl": thumbnail_url
    }