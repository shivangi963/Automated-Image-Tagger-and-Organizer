from fastapi import APIRouter, Depends, Query
from typing import List, Optional
from app.models import ImageResponse, SearchResponse, ImageTag, DuplicateGroup
from app.auth import get_current_user, get_user_id
from app.database import get_database
from app.ml.phash import hamming_distance, similarity_score
from bson import ObjectId
from datetime import datetime

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
    
    # Build search pipeline
    match_stage = {"user_id": user_id, "status": "completed"}
    
    # Date range filter
    if date_from or date_to:
        match_stage["created_at"] = {}
        if date_from:
            match_stage["created_at"]["$gte"] = date_from
        if date_to:
            match_stage["created_at"]["$lte"] = date_to
    
    # Tag filter
    image_ids = None
    if tags or query:
        tag_list = []
        if tags:
            tag_list.extend([t.strip().lower() for t in tags.split(",")])
        if query:
            # Text search on tags
            tag_cursor = db.tags.find(
                {"$text": {"$search": query}},
                {"score": {"$meta": "textScore"}}
            ).sort([("score", {"$meta": "textScore"})])
            
            found_tags = await tag_cursor.to_list(length=20)
            tag_list.extend([str(t["_id"]) for t in found_tags])
        
        if tag_list:
            # Find images with these tags
            tag_ids = []
            for tag_name in tag_list:
                if ObjectId.is_valid(tag_name):
                    tag_ids.append(ObjectId(tag_name))
                else:
                    tag_doc = await db.tags.find_one({"name": tag_name})
                    if tag_doc:
                        tag_ids.append(tag_doc["_id"])
            
            if tag_ids:
                image_tag_docs = await db.image_tags.find(
                    {"tag_id": {"$in": tag_ids}}
                ).distinct("image_id")
                
                image_ids = image_tag_docs
    
    if image_ids is not None:
        match_stage["_id"] = {"$in": image_ids}
    
    # Get total count
    total = await db.images.count_documents(match_stage)
    
    # Get images
    cursor = db.images.find(match_stage).sort("created_at", -1).skip(skip).limit(limit)
    images = await cursor.to_list(length=limit)
    
    # Build response
    result_images = []
    for img in images:
        tags = await get_image_tags_helper(str(img["_id"]), db)
        
        result_images.append(ImageResponse(
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
    
    return SearchResponse(total=total, images=result_images)


@router.get("/duplicates", response_model=List[DuplicateGroup])
async def find_duplicates(
    threshold: int = 8,
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
    
    # Find duplicates
    duplicate_groups = []
    processed = set()
    
    for i, img1 in enumerate(images):
        if img1["_id"] in processed:
            continue
        
        group = [img1]
        
        for img2 in images[i+1:]:
            if img2["_id"] in processed:
                continue
            
            distance = hamming_distance(img1["phash"], img2["phash"])
            
            if distance <= threshold:
                group.append(img2)
                processed.add(img2["_id"])
        
        if len(group) > 1:
            # Calculate average similarity
            similarities = []
            for j in range(len(group)):
                for k in range(j+1, len(group)):
                    sim = similarity_score(group[j]["phash"], group[k]["phash"])
                    similarities.append(sim)
            
            avg_similarity = sum(similarities) / len(similarities) if similarities else 0
            
            # Convert to ImageResponse
            image_responses = []
            for img in group:
                tags = await get_image_tags_helper(str(img["_id"]), db)
                image_responses.append(ImageResponse(
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
            
            duplicate_groups.append(DuplicateGroup(
                images=image_responses,
                similarity_score=round(avg_similarity, 3)
            ))
    
    return duplicate_groups


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