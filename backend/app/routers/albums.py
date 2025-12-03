from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from app.models import AlbumCreate, AlbumResponse, AlbumUpdate, AlbumAddImages, ImageResponse, ImageTag
from app.auth import get_current_user, get_user_id
from app.database import get_database
from datetime import datetime
from bson import ObjectId

router = APIRouter(prefix="/albums", tags=["Albums"])


@router.post("/", response_model=AlbumResponse, status_code=status.HTTP_201_CREATED)
async def create_album(
    album: AlbumCreate,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    """Create a new album"""
    user_id = get_user_id(current_user)
    
    album_doc = {
        "user_id": user_id,
        "name": album.name,
        "description": album.description,
        "created_at": datetime.utcnow()
    }
    
    result = await db.albums.insert_one(album_doc)
    
    return AlbumResponse(
        id=str(result.inserted_id),
        user_id=user_id,
        name=album.name,
        description=album.description,
        image_count=0,
        created_at=album_doc["created_at"]
    )


@router.get("/", response_model=List[AlbumResponse])
async def list_albums(
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    """List user's albums"""
    user_id = get_user_id(current_user)
    
    cursor = db.albums.find({"user_id": user_id}).sort("created_at", -1)
    albums = await cursor.to_list(length=100)
    
    result = []
    for album in albums:
        # Count images in album
        image_count = await db.album_images.count_documents({"album_id": album["_id"]})
        
        # Get cover image (first image in album)
        cover_image = None
        first_image = await db.album_images.find_one({"album_id": album["_id"]})
        if first_image:
            cover_image = str(first_image["image_id"])
        
        result.append(AlbumResponse(
            id=str(album["_id"]),
            user_id=album["user_id"],
            name=album["name"],
            description=album.get("description"),
            image_count=image_count,
            cover_image=cover_image,
            created_at=album["created_at"]
        ))
    
    return result


@router.get("/{album_id}", response_model=AlbumResponse)
async def get_album(
    album_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    """Get album details"""
    user_id = get_user_id(current_user)
    
    album = await db.albums.find_one({"_id": ObjectId(album_id), "user_id": user_id})
    if not album:
        raise HTTPException(status_code=404, detail="Album not found")
    
    image_count = await db.album_images.count_documents({"album_id": ObjectId(album_id)})
    
    first_image = await db.album_images.find_one({"album_id": ObjectId(album_id)})
    cover_image = str(first_image["image_id"]) if first_image else None
    
    return AlbumResponse(
        id=str(album["_id"]),
        user_id=album["user_id"],
        name=album["name"],
        description=album.get("description"),
        image_count=image_count,
        cover_image=cover_image,
        created_at=album["created_at"]
    )


@router.put("/{album_id}", response_model=AlbumResponse)
async def update_album(
    album_id: str,
    album_update: AlbumUpdate,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    """Update album"""
    user_id = get_user_id(current_user)
    
    album = await db.albums.find_one({"_id": ObjectId(album_id), "user_id": user_id})
    if not album:
        raise HTTPException(status_code=404, detail="Album not found")
    
    update_data = {}
    if album_update.name is not None:
        update_data["name"] = album_update.name
    if album_update.description is not None:
        update_data["description"] = album_update.description
    
    if update_data:
        await db.albums.update_one(
            {"_id": ObjectId(album_id)},
            {"$set": update_data}
        )
    
    return await get_album(album_id, current_user, db)


@router.delete("/{album_id}")
async def delete_album(
    album_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    """Delete album"""
    user_id = get_user_id(current_user)
    
    album = await db.albums.find_one({"_id": ObjectId(album_id), "user_id": user_id})
    if not album:
        raise HTTPException(status_code=404, detail="Album not found")
    
    # Delete album and associations
    await db.albums.delete_one({"_id": ObjectId(album_id)})
    await db.album_images.delete_many({"album_id": ObjectId(album_id)})
    
    return {"message": "Album deleted successfully"}


@router.post("/{album_id}/images")
async def add_images_to_album(
    album_id: str,
    data: AlbumAddImages,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    """Add images to album"""
    user_id = get_user_id(current_user)
    
    # Verify album ownership
    album = await db.albums.find_one({"_id": ObjectId(album_id), "user_id": user_id})
    if not album:
        raise HTTPException(status_code=404, detail="Album not found")
    
    # Add images
    added = 0
    for image_id in data.image_ids:
        # Verify image ownership
        image = await db.images.find_one({"_id": ObjectId(image_id), "user_id": user_id})
        if not image:
            continue
        
        # Add to album (upsert to avoid duplicates)
        await db.album_images.update_one(
            {"album_id": ObjectId(album_id), "image_id": ObjectId(image_id)},
            {"$set": {"added_at": datetime.utcnow()}},
            upsert=True
        )
        added += 1
    
    return {"message": f"Added {added} images to album"}


@router.delete("/{album_id}/images/{image_id}")
async def remove_image_from_album(
    album_id: str,
    image_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    """Remove image from album"""
    user_id = get_user_id(current_user)
    
    # Verify album ownership
    album = await db.albums.find_one({"_id": ObjectId(album_id), "user_id": user_id})
    if not album:
        raise HTTPException(status_code=404, detail="Album not found")
    
    # Remove image
    await db.album_images.delete_one({
        "album_id": ObjectId(album_id),
        "image_id": ObjectId(image_id)
    })
    
    return {"message": "Image removed from album"}


@router.get("/{album_id}/images", response_model=List[ImageResponse])
async def get_album_images(
    album_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    """Get all images in an album"""
    user_id = get_user_id(current_user)
    
    # Verify album ownership
    album = await db.albums.find_one({"_id": ObjectId(album_id), "user_id": user_id})
    if not album:
        raise HTTPException(status_code=404, detail="Album not found")
    
    # Get image IDs from album
    album_images = await db.album_images.find({"album_id": ObjectId(album_id)}).to_list(length=1000)
    image_ids = [ai["image_id"] for ai in album_images]
    
    if not image_ids:
        return []
    
    # Get images
    cursor = db.images.find({"_id": {"$in": image_ids}})
    images = await cursor.to_list(length=1000)
    
    result = []
    for img in images:
        tags = await get_image_tags_helper(str(img["_id"]), db)
        
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


async def get_image_tags_helper(image_id: str, db) -> List[ImageTag]:
    """Helper to get image tags"""
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