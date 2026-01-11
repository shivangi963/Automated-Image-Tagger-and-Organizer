from fastapi import APIRouter, Depends, Query
from typing import List, Optional
from app.models import ImageResponse, SearchResponse, ImageTag, DuplicateGroup
from app.auth import get_current_user, get_user_id
from app.database import get_database
from app.ml.phash import hamming_distance, similarity_score
from bson import ObjectId
from datetime import datetime
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/search", tags=["Search"])


@router.get("/", response_model=SearchResponse)
async def search_images(
    query: Optional[str] = None,
    tags: Optional[str] = Query(None, description="Comma-separated tags"),
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    skip: int = 0,
    limit: int = 50,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    """Search images by keywords and filters"""
    user_id = get_user_id(current_user)
    
    # Build search filter
    match_stage = {"user_id": user_id, "status": "completed"}
    
    # Date range filter
    if date_from or date_to:
        match_stage["created_at"] = {}
        if date_from:
            match_stage["created_at"]["$gte"] = date_from
        if date_to:
            match_stage["created_at"]["$lte"] = date_to
    
    # FIXED: Text search on tag_strings
    if query or tags:
        search_terms = []
        
        if query:
            # Use MongoDB text search
            match_stage["$text"] = {"$search": query.strip()}
        
        if tags:
            # Split tags and search in tag_strings array
            tag_list = [t.strip().lower() for t in tags.split(",") if t.strip()]
            if tag_list:
                match_stage["tag_strings"] = {"$in": tag_list}
    
    logger.info(f"Search query: {match_stage}")
    
    # Get total count
    total = await db.images.count_documents(match_stage)
    
    # Get images
    cursor = db.images.find(match_stage).sort("created_at", -1).skip(skip).limit(limit)
    images = await cursor.to_list(length=limit)
    
    # Build response
    result_images = []
    for img in images:
        # Tags are now stored directly in the image document
        tags_list = img.get("tags", [])
        
        result_images.append(ImageResponse(
            id=str(img["_id"]),
            user_id=img["user_id"],
            storage_key=img["storage_key"],
            original_filename=img["original_filename"],
            mime_type=img["mime_type"],
            metadata=img.get("metadata"),
            phash=img.get("phash"),
            tags=tags_list,  # Tags already in correct format
            status=img["status"],
            created_at=img["created_at"],
            processed_at=img.get("processed_at"),
            thumbnailUrl=None  # Will be added by frontend
        ))
    
    logger.info(f"Search returned {len(result_images)} results out of {total} total")
    return SearchResponse(total=total, images=result_images)


@router.get("/duplicates", response_model=List[DuplicateGroup])
async def find_duplicates(
    threshold: int = 10,  # FIXED: Increased threshold for better detection
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    """Find potential duplicate images based on pHash"""
    user_id = get_user_id(current_user)
    
    # Get all images with pHash
    cursor = db.images.find({
        "user_id": user_id,
        "phash": {"$exists": True, "$ne": None}
    })
    images = await cursor.to_list(length=1000)
    
    logger.info(f"Checking {len(images)} images for duplicates with threshold {threshold}")
    
    # Find duplicates
    duplicate_groups = []
    processed = set()
    
    for i, img1 in enumerate(images):
        img1_id = str(img1["_id"])
        if img1_id in processed:
            continue
        
        group = [img1]
        
        for img2 in images[i+1:]:
            img2_id = str(img2["_id"])
            if img2_id in processed:
                continue
            
            try:
                distance = hamming_distance(img1["phash"], img2["phash"])
                logger.debug(f"Distance between {img1['original_filename']} and {img2['original_filename']}: {distance}")
                
                if distance <= threshold:
                    group.append(img2)
                    processed.add(img2_id)
            except Exception as e:
                logger.error(f"Error comparing hashes: {e}")
                continue
        
        if len(group) > 1:
            # Calculate average similarity
            similarities = []
            for j in range(len(group)):
                for k in range(j+1, len(group)):
                    try:
                        sim = similarity_score(group[j]["phash"], group[k]["phash"])
                        similarities.append(sim)
                    except Exception as e:
                        logger.error(f"Error calculating similarity: {e}")
            
            avg_similarity = sum(similarities) / len(similarities) if similarities else 0
            
            # Convert to ImageResponse
            image_responses = []
            for img in group:
                # Get tags from image document
                tags_list = img.get("tags", [])
                
                image_responses.append(ImageResponse(
                    id=str(img["_id"]),
                    user_id=img["user_id"],
                    storage_key=img["storage_key"],
                    original_filename=img["original_filename"],
                    mime_type=img["mime_type"],
                    metadata=img.get("metadata"),
                    phash=img.get("phash"),
                    tags=tags_list,
                    status=img["status"],
                    created_at=img["created_at"],
                    processed_at=img.get("processed_at"),
                    thumbnailUrl=None
                ))
            
            duplicate_groups.append(DuplicateGroup(
                images=image_responses,
                similarity_score=round(avg_similarity, 3)
            ))
            
            logger.info(f"Found duplicate group of {len(group)} images with {avg_similarity:.1%} similarity")
    
    logger.info(f"Total duplicate groups found: {len(duplicate_groups)}")
    return duplicate_groups