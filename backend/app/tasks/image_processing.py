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
        logger.info(f"Starting processing for image {image_id}")
        
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
        
        logger.info(f"Downloaded {len(image_data)} bytes")
        
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
            logger.info(f"YOLO returned {len(detections)} detections")
            
            unique_labels = detector.extract_unique_labels(detections)
            logger.info(f"Extracted {len(unique_labels)} unique labels")
            
            # Store tags directly in the image document
            tag_docs = []
            tag_strings = []  # For text search
            
            for label_info in unique_labels:
                label = label_info['label']
                confidence = label_info['confidence']
                
                tag_docs.append({
                    "tag_name": label,
                    "confidence": confidence,
                    "source": "yolo"
                })
                
                # Add to searchable strings
                tag_strings.append(label.lower())
            
            logger.info(f"Created {len(tag_docs)} tags: {tag_strings[:10]}")
            
        finally:
            # Clean up temp file
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        
        # Update image document with tags stored inline
        update_result = db.images.update_one(
            {"_id": ObjectId(image_id)},
            {
                "$set": {
                    "metadata": metadata,
                    "phash": phash,
                    "thumbnail_key": thumb_key,
                    "tags": tag_docs,  # Store tags directly
                    "tag_strings": tag_strings,  # For text search
                    "status": "completed",
                    "processed_at": datetime.utcnow()
                }
            }
        )
        
        logger.info(f"Successfully processed image {image_id} with {len(tag_docs)} tags (modified: {update_result.modified_count})")
        
        return {
            "status": "success",
            "image_id": image_id,
            "tags_count": len(tag_docs),
            "tags": tag_strings[:10]  # Return first 10 for logging
        }
        
    except Exception as e:
        logger.exception(f"Error processing image {image_id}: {e}")
        
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