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
    """Get MongoDB database connection using URI"""
    client = MongoClient(settings.MONGODB_URI)
    return client[settings.database_name]


@celery_app.task(bind=True, name="process_image", max_retries=3)
def process_image(self, image_id: str):
    """
    Process uploaded image with comprehensive error handling:
    1. Download from MinIO
    2. Extract metadata and EXIF
    3. Generate thumbnail
    4. Compute pHash for duplicate detection
    5. Run YOLO detection
    6. Save tags to database
    """
    db = get_db()
    
    try:
        logger.info(f"Starting image processing for {image_id}")
        
        # Update status to processing
        db.images.update_one(
            {"_id": ObjectId(image_id)},
            {
                "$set": {
                    "status": "processing",
                    "processing_started_at": datetime.utcnow()
                }
            }
        )
        
        # Get image record
        image_doc = db.images.find_one({"_id": ObjectId(image_id)})
        if not image_doc:
            raise Exception(f"Image {image_id} not found in database")
        
        storage_key = image_doc["storage_key"]
        
        # Download image from MinIO
        logger.info(f"Downloading image from storage: {storage_key}")
        image_data = storage.download_file(storage_key)
        if not image_data:
            raise Exception("Failed to download image from storage")
        
        # Open and validate image
        try:
            image = Image.open(BytesIO(image_data))
            image.verify()  # Verify it's a valid image
            image = Image.open(BytesIO(image_data))  # Reopen after verify
        except Exception as e:
            raise Exception(f"Invalid or corrupted image file: {e}")
        
        # Convert RGBA to RGB if necessary
        if image.mode == 'RGBA':
            background = Image.new('RGB', image.size, (255, 255, 255))
            background.paste(image, mask=image.split()[3])
            image = background
        elif image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Extract metadata
        metadata = {
            "width": image.width,
            "height": image.height,
            "format": image.format or "JPEG",
            "mode": image.mode,
            "size_bytes": len(image_data)
        }
        
        # Extract EXIF data if available
        exif_data = {}
        if hasattr(image, '_getexif') and image._getexif():
            try:
                exif = image._getexif()
                if exif:
                    # Only save important EXIF data
                    important_tags = {
                        271: 'Make',
                        272: 'Model',
                        274: 'Orientation',
                        306: 'DateTime',
                        36867: 'DateTimeOriginal',
                        33434: 'ExposureTime',
                        33437: 'FNumber',
                        34855: 'ISOSpeedRatings'
                    }
                    for tag, name in important_tags.items():
                        if tag in exif:
                            exif_data[name] = str(exif[tag])
                    
                    if exif_data:
                        metadata["exif"] = exif_data
            except Exception as e:
                logger.warning(f"Failed to extract EXIF: {e}")
        
        # Generate thumbnail
        logger.info("Generating thumbnail")
        thumbnail = image.copy()
        thumbnail.thumbnail(
            (settings.THUMBNAIL_SIZE, settings.THUMBNAIL_SIZE), 
            Image.Resampling.LANCZOS
        )
        
        thumb_buffer = BytesIO()
        thumbnail.save(thumb_buffer, format='JPEG', quality=settings.IMAGE_QUALITY, optimize=True)
        thumb_data = thumb_buffer.getvalue()
        
        # Upload thumbnail
        thumb_key = f"thumbnails/{storage_key.split('/')[-1]}"
        thumb_success = storage.upload_file(thumb_data, thumb_key, "image/jpeg")
        if not thumb_success:
            logger.warning("Failed to upload thumbnail, continuing without it")
            thumb_key = None
        
        # Save image to temporary file for YOLO processing
        with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as tmp_file:
            image.save(tmp_file, format='JPEG', quality=95)
            tmp_path = tmp_file.name
        
        try:
            # Compute perceptual hash for duplicate detection
            logger.info("Computing perceptual hash")
            phash = compute_phash(tmp_path)
            
            # Run YOLO detection
            logger.info("Running YOLO object detection")
            detections = detector.detect_objects(tmp_path)
            unique_labels = detector.extract_unique_labels(detections)
            
            logger.info(f"Detected {len(unique_labels)} unique objects")
            
            # Save tags to database
            tag_count = 0
            for label_info in unique_labels:
                label = label_info['label']
                confidence = label_info['confidence']
                
                # Find or create tag
                tag = db.tags.find_one({"name": label.lower()})
                if not tag:
                    tag_result = db.tags.insert_one({
                        "name": label.lower(),
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
                tag_count += 1
            
        finally:
            # Clean up temporary file
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        
        # Update image document with all processed data
        update_data = {
            "metadata": metadata,
            "phash": phash,
            "status": "completed",
            "processed_at": datetime.utcnow(),
            "tag_count": tag_count
        }
        
        if thumb_key:
            update_data["thumbnail_key"] = thumb_key
        
        db.images.update_one(
            {"_id": ObjectId(image_id)},
            {"$set": update_data}
        )
        
        logger.info(f"✓ Successfully processed image {image_id} with {tag_count} tags")
        
        return {
            "status": "success",
            "image_id": image_id,
            "tags_count": tag_count,
            "phash": phash
        }
        
    except Exception as e:
        logger.error(f"Error processing image {image_id}: {e}", exc_info=True)
        
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
        
        # Retry logic
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying image processing (attempt {self.request.retries + 1})")
            raise self.retry(exc=e, countdown=60 * (self.request.retries + 1))
        
        raise


@celery_app.task(name="cleanup_failed_uploads")
def cleanup_failed_uploads():
    """Cleanup images stuck in pending state for more than 30 minutes"""
    db = get_db()
    
    try:
        from datetime import timedelta
        threshold = datetime.utcnow() - timedelta(minutes=30)
        
        failed_images = db.images.find({
            "status": "pending",
            "created_at": {"$lt": threshold}
        })
        
        count = 0
        for image in failed_images:
            # Delete from storage
            storage.delete_file(image["storage_key"])
            # Delete from database
            db.images.delete_one({"_id": image["_id"]})
            count += 1
        
        if count > 0:
            logger.info(f"Cleaned up {count} failed uploads")
        
        return {"cleaned": count}
        
    except Exception as e:
        logger.error(f"Failed to cleanup uploads: {e}")
        raise