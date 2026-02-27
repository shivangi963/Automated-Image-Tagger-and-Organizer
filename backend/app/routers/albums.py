from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from app.models import AlbumCreate, AlbumResponse, AlbumUpdate, AlbumAddImages, ImageTag
from app.auth import get_current_user, get_user_id
from app.database import get_database
from app.storage import storage
from datetime import datetime
from bson import ObjectId
import logging

router = APIRouter(prefix="/albums", tags=["Albums"])
logger = logging.getLogger(__name__)


def _make_image_dict(img: dict) -> dict:
    """Build image dict with embedded URLs (same as images router)."""
    img_id = str(img["_id"])
    storage_key = img.get("storage_key", "")
    thumbnail_key = img.get("thumbnail_key")

    url = storage.get_presigned_url(storage_key) if storage_key else None
    thumbnail_url = storage.get_presigned_url(thumbnail_key) if thumbnail_key else url

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
        "status": img.get("status", "pending"),
        "created_at": img.get("created_at"),
        "processed_at": img.get("processed_at"),
        "url": url,
        "thumbnailUrl": thumbnail_url,
    }


@router.post("/", response_model=AlbumResponse, status_code=status.HTTP_201_CREATED)
async def create_album(
    album: AlbumCreate,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_database),
):
    user_id = get_user_id(current_user)
    album_doc = {
        "user_id": user_id,
        "name": album.name,
        "description": album.description,
        "created_at": datetime.utcnow(),
    }
    result = await db.albums.insert_one(album_doc)
    return AlbumResponse(
        id=str(result.inserted_id),
        user_id=user_id,
        name=album.name,
        description=album.description,
        image_count=0,
        cover_image=None,
        created_at=album_doc["created_at"],
    )


@router.get("/", response_model=List[AlbumResponse])
async def list_albums(
    current_user: dict = Depends(get_current_user),
    db=Depends(get_database),
):
    user_id = get_user_id(current_user)
    cursor = db.albums.find({"user_id": user_id}).sort("created_at", -1)
    albums = await cursor.to_list(length=100)

    result = []
    for album in albums:
        album_oid = album["_id"]
        image_count = await db.album_images.count_documents({"album_id": album_oid})

        # Get cover image presigned URL (not raw ObjectId)
        cover_image = None
        first_link = await db.album_images.find_one({"album_id": album_oid})
        if first_link:
            cover_img = await db.images.find_one({"_id": first_link["image_id"]})
            if cover_img and cover_img.get("storage_key"):
                # Use thumbnail if available, otherwise original
                key = cover_img.get("thumbnail_key") or cover_img["storage_key"]
                cover_image = storage.get_presigned_url(key)

        result.append(AlbumResponse(
            id=str(album_oid),
            user_id=album["user_id"],
            name=album["name"],
            description=album.get("description"),
            image_count=image_count,
            cover_image=cover_image,
            created_at=album["created_at"],
        ))
    return result


@router.get("/{album_id}", response_model=AlbumResponse)
async def get_album(
    album_id: str,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_database),
):
    user_id = get_user_id(current_user)
    album = await db.albums.find_one({"_id": ObjectId(album_id), "user_id": user_id})
    if not album:
        raise HTTPException(status_code=404, detail="Album not found")

    album_oid = ObjectId(album_id)
    image_count = await db.album_images.count_documents({"album_id": album_oid})

    cover_image = None
    first_link = await db.album_images.find_one({"album_id": album_oid})
    if first_link:
        cover_img = await db.images.find_one({"_id": first_link["image_id"]})
        if cover_img and cover_img.get("storage_key"):
            key = cover_img.get("thumbnail_key") or cover_img["storage_key"]
            cover_image = storage.get_presigned_url(key)

    return AlbumResponse(
        id=str(album["_id"]),
        user_id=album["user_id"],
        name=album["name"],
        description=album.get("description"),
        image_count=image_count,
        cover_image=cover_image,
        created_at=album["created_at"],
    )


@router.put("/{album_id}", response_model=AlbumResponse)
async def update_album(
    album_id: str,
    album_update: AlbumUpdate,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_database),
):
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
        await db.albums.update_one({"_id": ObjectId(album_id)}, {"$set": update_data})

    return await get_album(album_id, current_user, db)


@router.delete("/{album_id}")
async def delete_album(
    album_id: str,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_database),
):
    user_id = get_user_id(current_user)
    album = await db.albums.find_one({"_id": ObjectId(album_id), "user_id": user_id})
    if not album:
        raise HTTPException(status_code=404, detail="Album not found")

    await db.albums.delete_one({"_id": ObjectId(album_id)})
    await db.album_images.delete_many({"album_id": ObjectId(album_id)})
    return {"message": "Album deleted successfully"}


@router.post("/{album_id}/images")
async def add_images_to_album(
    album_id: str,
    data: AlbumAddImages,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_database),
):
    user_id = get_user_id(current_user)
    album = await db.albums.find_one({"_id": ObjectId(album_id), "user_id": user_id})
    if not album:
        raise HTTPException(status_code=404, detail="Album not found")

    added = 0
    for image_id in data.image_ids:
        image = await db.images.find_one({"_id": ObjectId(image_id), "user_id": user_id})
        if not image:
            continue
        await db.album_images.update_one(
            {"album_id": ObjectId(album_id), "image_id": ObjectId(image_id)},
            {"$set": {"added_at": datetime.utcnow()}},
            upsert=True,
        )
        added += 1

    return {"message": f"Added {added} images to album"}


@router.delete("/{album_id}/images/{image_id}")
async def remove_image_from_album(
    album_id: str,
    image_id: str,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_database),
):
    user_id = get_user_id(current_user)
    album = await db.albums.find_one({"_id": ObjectId(album_id), "user_id": user_id})
    if not album:
        raise HTTPException(status_code=404, detail="Album not found")

    await db.album_images.delete_one({
        "album_id": ObjectId(album_id),
        "image_id": ObjectId(image_id),
    })
    return {"message": "Image removed from album"}


@router.get("/{album_id}/images", response_model=List[dict])
async def get_album_images(
    album_id: str,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_database),
):
    """Return album images with embedded presigned URLs."""
    user_id = get_user_id(current_user)
    album = await db.albums.find_one({"_id": ObjectId(album_id), "user_id": user_id})
    if not album:
        raise HTTPException(status_code=404, detail="Album not found")

    links = await db.album_images.find({"album_id": ObjectId(album_id)}).to_list(length=1000)
    image_ids = [link["image_id"] for link in links]

    if not image_ids:
        return []

    images = await db.images.find({"_id": {"$in": image_ids}}).to_list(length=1000)
    return [_make_image_dict(img) for img in images]