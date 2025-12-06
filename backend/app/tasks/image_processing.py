from celery_worker import celery_app
from app.storage import storage
from app.ml.yolo_detector import detector
from app.ml.phash import compute_phash
from PIL import Image
from io import BytesIO
import logging
from datetime import datetime
from pymongo import MongoClient
from bson import ObjectId
from app.config import settings
import tempfile
import os

logger = logging.getLogger(__name__)


def get_db():
    """Get MongoDB database connection"""
    client = MongoClient(settings.MONGODB_URL)
    return client[settings.MONGODB_DB]


@celery_app.task(bind=True, name="process_image")
def process_image(self, image_id: str):
    """
    Process uploaded image:
    1. Download from MinIO
    2. Extract metadata
    3. Generate thumbnail
    4. Compute pHash
    5. Run YOLO detection
    6. Save tags to database
    """
    db = get_db()
    
    try:
        # Update status to processing
        db.images.update_one(
            {"_id": ObjectId(image_id)},
            {"$set": {"status": "processing"}}
        )
        
        # Get image record
        image_doc = db.images.find_one({"_id": ObjectId(image_id)})
        if not image_doc:
            raise Exception(f"Image {image_id} not found")
        
        storage_key = image_doc["storage_key"]
        
        # Download image from MinIO
        logger.info(f"Downloading image: {storage_key}")
        image_data = storage.download_file(storage_key)
        if not image_data:
            raise Exception("Failed to download image")
        
        # Open image
        image = Image.open(BytesIO(image_data))
        
        # Extract metadata
        metadata = {
            "width": image.width,
            "height": image.height,
            "format": image.format,
            "mode": image.mode,
            "size_bytes": len(image_data)
        }
        
        # Extract EXIF if available
        if hasattr(image, '_getexif') and image._getexif():
            metadata["exif"] = dict(image._getexif())
        
        # Generate thumbnail
        thumbnail = image.copy()
        thumbnail.thumbnail((300, 300), Image.Resampling.LANCZOS)
        
        thumb_buffer = BytesIO()
        thumbnail.save(thumb_buffer, format='JPEG', quality=85)
        thumb_data = thumb_buffer.getvalue()
        
        # Upload thumbnail
        thumb_key = f"thumbnails/{storage_key}"
        storage.upload_file(thumb_data, thumb_key, "image/jpeg")
        
        # Save image to temp file for YOLO processing
        with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as tmp_file:
            tmp_file.write(image_data)
            tmp_path = tmp_file.name
        
        try:
            # Compute pHash
            logger.info("Computing perceptual hash")
            phash = compute_phash(tmp_path)
            
            # Run YOLO detection
            logger.info("Running YOLO detection")
            detections = detector.detect_objects(tmp_path)
            unique_labels = detector.extract_unique_labels(detections)
            
            # Save tags to database
            tag_docs = []
            for label_info in unique_labels:
                label = label_info['label']
                confidence = label_info['confidence']
                
                # Find or create tag
                tag = db.tags.find_one({"name": label})
                if not tag:
                    tag_result = db.tags.insert_one({
                        "name": label,
                        "source": "yolo",
                        "created_at": datetime.utcnow()
                    })
                    tag_id = tag_result.inserted_id
                else:
                    tag_id = tag["_id"]
                
                # Create image-tag association
                db.image_tags.update_one(
                    {"image_id": ObjectId(image_id), "tag_id": tag_id},
                    {
                        "$set": {
                            "confidence": confidence,
                            "source": "yolo",
                            "created_at": datetime.utcnow()
                        }
                    },
                    upsert=True
                )
                
                tag_docs.append({
                    "tag_name": label,
                    "confidence": confidence,
                    "source": "yolo"
                })
            
        finally:
            # Clean up temp file
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        
        # Update image document
        db.images.update_one(
            {"_id": ObjectId(image_id)},
            {
                "$set": {
                    "metadata": metadata,
                    "phash": phash,
                    "thumbnail_key": thumb_key,
                    "status": "completed",
                    "processed_at": datetime.utcnow()
                }
            }
        )
        
        logger.info(f"Successfully processed image {image_id}")
        return {
            "status": "success",
            "image_id": image_id,
            "tags_count": len(tag_docs)
        }
        
    except Exception as e:
        logger.error(f"Error processing image {image_id}: {e}")
        
        # Update status to failed
        db.images.update_one(
            {"_id": ObjectId(image_id)},
            {
                "$set": {
                    "status": "failed",
                    "error": str(e),
                    "processed_at": datetime.utcnow()
                }
            }
        )
        raise


async def process_image_sync(image_id: str, db, storage_client):
    """Process image synchronously (extract metadata, tags, thumbnail)"""
    try:
        image = await db.images.find_one({"_id": ObjectId(image_id)})
        if not image:
            logger.error(f"Image not found: {image_id}")
            return
        
        logger.info(f"Processing image: {image_id}")
        
        # Download image from MinIO
        file_bytes = storage_client.get_file(image["storage_key"])
        if not file_bytes:
            raise Exception("Failed to download image from storage")
        
        # Extract metadata (simplified)
        metadata = {
            "size": len(file_bytes),
            "format": image["mime_type"]
        }
        
        # Create thumbnail (simplified - just store original for now)
        thumbnail_key = image["storage_key"]  # TODO: create actual thumbnail
        
        # Update image document
        await db.images.update_one(
            {"_id": ObjectId(image_id)},
            {
                "$set": {
                    "status": "completed",
                    "metadata": metadata,
                    "thumbnail_key": thumbnail_key,
                    "processed_at": datetime.utcnow()
                }
            }
        )
        
        logger.info(f"Image processed successfully: {image_id}")
        
    except Exception as e:
        logger.exception(f"Error processing image {image_id}: {e}")
        await db.images.update_one(
            {"_id": ObjectId(image_id)},
            {"$set": {"status": "error", "error": str(e)}}
        )