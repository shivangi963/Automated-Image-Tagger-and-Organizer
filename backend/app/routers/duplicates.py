"""
/duplicates  —  find near-duplicate images using pHash Hamming distance
"""
from fastapi import APIRouter, Depends
from typing import List
from bson import ObjectId
from app.ml.phash import find_duplicates
from app.auth import get_current_user, get_db

router = APIRouter(prefix="/duplicates", tags=["duplicates"])


@router.get("/", summary="Find duplicate images in your library")
async def get_duplicates(
    threshold: int = 10,
    current_user=Depends(get_current_user),
    db=Depends(get_db),
):
    """
    Scans all processed images belonging to the current user,
    compares their perceptual hashes and returns groups of near-duplicates.

    - **threshold**: max Hamming distance to consider two images duplicates
      (default 10; lower = stricter match)
    """
    # Fetch all images that have a phash
    cursor = db["images"].find(
        {"user_id": ObjectId(current_user["_id"]), "phash": {"$ne": None}},
        {"_id": 1, "phash": 1, "original_filename": 1, "storage_key": 1, "thumbnail_key": 1},
    )
    images = await cursor.to_list(length=5000)

    if not images:
        return {"groups": [], "total_duplicates": 0}

    # Build (id, hash) pairs
    pairs = [(str(img["_id"]), img["phash"]) for img in images]
    groups = find_duplicates(pairs, threshold=threshold)  # type: ignore[call-arg]

    # Enrich groups with image info
    id_to_img = {str(img["_id"]): img for img in images}
    enriched = []
    for group in groups:
        enriched.append(
            [
                {
                    "id": img_id,
                    "filename": id_to_img[img_id].get("original_filename", ""),
                    "storage_key": id_to_img[img_id].get("storage_key", ""),
                }
                for img_id in group
                if img_id in id_to_img
            ]
        )

    return {
        "groups": enriched,
        "total_duplicates": sum(len(g) for g in enriched),
        "groups_count": len(enriched),
    }