"""
/duplicates  —  find near-duplicate images using pHash Hamming distance
"""
from fastapi import APIRouter, Depends
from typing import List
from bson import ObjectId
from app.ml.phash import find_duplicates
from app.auth import get_current_user, get_user_id
from app.database import get_database
from app.storage import storage

router = APIRouter(prefix="/duplicates", tags=["Duplicates"])


def _make_image_dict(img: dict) -> dict:
    """Build image dict with embedded presigned URLs."""
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


@router.get("/", summary="Find duplicate images in your library")
async def get_duplicates(
    threshold: int = 10,
    current_user=Depends(get_current_user),
    db=Depends(get_database),
):
    """
    Scans all processed images belonging to the current user,
    compares their perceptual hashes and returns groups of near-duplicates.

    - **threshold**: max Hamming distance to consider two images duplicates
      (default 10; lower = stricter match)
    """
    user_id = get_user_id(current_user)

    cursor = db["images"].find(
        {"user_id": user_id, "phash": {"$ne": None}},
        {"_id": 1, "phash": 1, "original_filename": 1, "storage_key": 1,
         "thumbnail_key": 1, "tags": 1, "metadata": 1, "status": 1,
         "created_at": 1, "processed_at": 1, "mime_type": 1, "user_id": 1},
    )
    images = await cursor.to_list(length=5000)

    if not images:
        return {"groups": [], "total_duplicates": 0, "groups_count": 0}

    # Build (id, hash) pairs
    pairs = [(str(img["_id"]), img["phash"]) for img in images]
    groups = find_duplicates(pairs, threshold=threshold)

    # Enrich groups with full image info including presigned URLs
    id_to_img = {str(img["_id"]): img for img in images}
    enriched = []
    for group in groups:
        enriched.append(
            [_make_image_dict(id_to_img[img_id]) for img_id in group if img_id in id_to_img]
        )

    return {
        "groups": enriched,
        "total_duplicates": sum(len(g) for g in enriched),
        "groups_count": len(enriched),
    }