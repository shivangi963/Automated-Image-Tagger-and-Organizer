from fastapi import APIRouter, Depends, Query
from typing import List, Optional
from app.models import DuplicateGroup
from app.auth import get_current_user, get_user_id
from app.database import get_database
from app.storage import storage
from app.ml.phash import hamming_distance, similarity_score
from bson import ObjectId
from datetime import datetime
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/search", tags=["Search"])


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
        "caption": img.get("caption"),
        "ocr_text": img.get("ocr_text"),
        "ocr_regions": img.get("ocr_regions", []),
    }


@router.get("/")
async def search_images(
    query: Optional[str] = None,
    tags: Optional[str] = Query(None, description="Comma-separated tags"),
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    skip: int = 0,
    limit: int = 50,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_database),
):
    """Search images by keywords/tags with presigned URLs embedded in results."""
    user_id = get_user_id(current_user)

    match_stage = {"user_id": user_id, "status": "completed"}

    if date_from or date_to:
        match_stage["created_at"] = {}
        if date_from:
            match_stage["created_at"]["$gte"] = date_from
        if date_to:
            match_stage["created_at"]["$lte"] = date_to

    if query:
        match_stage["$text"] = {"$search": query.strip()}

    if tags:
        tag_list = [t.strip().lower() for t in tags.split(",") if t.strip()]
        if tag_list:
            match_stage["tag_strings"] = {"$in": tag_list}

    logger.info(f"Search filter: {match_stage}")

    total = await db.images.count_documents(match_stage)
    cursor = db.images.find(match_stage).sort("created_at", -1).skip(skip).limit(limit)
    images = await cursor.to_list(length=limit)

    result_images = [_make_image_dict(img) for img in images]

    logger.info(f"Search returned {len(result_images)}/{total} results")
    return {"total": total, "images": result_images}


@router.get("/duplicates")
async def find_duplicates(
    threshold: int = 10,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_database),
):
    """Find duplicate images by pHash with presigned URLs embedded."""
    user_id = get_user_id(current_user)

    cursor = db.images.find({
        "user_id": user_id,
        "phash": {"$exists": True, "$ne": None},
    })
    images = await cursor.to_list(length=1000)

    logger.info(f"Checking {len(images)} images for duplicates (threshold={threshold})")

    duplicate_groups = []
    processed = set()

    for i, img1 in enumerate(images):
        img1_id = str(img1["_id"])
        if img1_id in processed:
            continue

        group = [img1]

        for img2 in images[i + 1:]:
            img2_id = str(img2["_id"])
            if img2_id in processed:
                continue
            try:
                distance = hamming_distance(img1["phash"], img2["phash"])
                if distance <= threshold:
                    group.append(img2)
                    processed.add(img2_id)
            except Exception as e:
                logger.error(f"Hash comparison error: {e}")

        if len(group) > 1:
            similarities = []
            for j in range(len(group)):
                for k in range(j + 1, len(group)):
                    try:
                        sim = similarity_score(group[j]["phash"], group[k]["phash"])
                        similarities.append(sim)
                    except Exception:
                        pass

            avg_similarity = sum(similarities) / len(similarities) if similarities else 0

            duplicate_groups.append({
                "images": [_make_image_dict(img) for img in group],
                "similarity_score": round(avg_similarity, 3),
            })

    logger.info(f"Found {len(duplicate_groups)} duplicate groups")
    return duplicate_groups