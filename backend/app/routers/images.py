from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from typing import List, Optional
from app.models import ImageResponse, ImageTag, ImageUpdate, PresignRequest
from app.auth import get_current_user, get_user_id
from app.database import get_database
from app.storage import storage
from app.tasks.image_processing import process_image
from datetime import datetime
from bson import ObjectId
import logging

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


@router.get("/", response_model=List[ImageResponse])
async def list_images(
    skip: int = 0,
    limit: int = 50,
    status_filter: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    """List user's images"""
    user_id = get_user_id(current_user)
    
    query = {"user_id": user_id}
    if status_filter:
        query["status"] = status_filter
    
    cursor = db.images.find(query).sort("created_at", -1).skip(skip).limit(limit)
    images = await cursor.to_list(length=limit)
    
    result = []
    for img in images:
        # Get tags for this image
        tags = await get_image_tags(str(img["_id"]), db)
        
        result.append(ImageResponse(
            id=str(img["_id"]),
            user_id=img["user_id"],
            storage_key=img["storage_key"],
            original_filename=img["original_filename"],
            mime_type=img["mime_type"],
            metadata=img.get("metadata"),
            phash=img.get("phash"),
            tags=tags,
            status=img["status"],
            created_at=img["created_at"],
            processed_at=img.get("processed_at"),
            thumbnail_key=img.get("thumbnail_key")
        ))
    
    return result


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


@router.post("/presign")
async def presign_upload(request: PresignRequest, user_id: str = Depends(get_user_id)):
    """Generate presigned URL for direct S3/MinIO upload"""
    key = storage.generate_key(user_id, request.filename)
    presigned_url = storage.get_presigned_url(key, request.mime)
    return {
        "url": presigned_url,
        "storageKey": key
    }


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