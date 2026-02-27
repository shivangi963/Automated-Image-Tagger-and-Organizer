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
    """
    Get a synchronous MongoDB connection for Celery tasks.
    Uses the same MONGODB_URL from settings (including auth credentials).
    """
    client = MongoClient(
        settings.MONGODB_URL,
        serverSelectionTimeoutMS=5000,
    )
    return client[settings.MONGODB_DB]


def _extract_clean_exif(image: Image.Image) -> dict:
    """Extract EXIF data, skipping non-serializable values."""
    try:
        raw = image._getexif()
        if not raw:
            return {}
        clean = {}
        for k, v in raw.items():
            try:
                # Only keep simple serializable types
                if isinstance(v, (str, int, float, bool)):
                    clean[str(k)] = v
            except Exception:
                pass
        return clean
    except Exception:
        return {}


@celery_app.task(bind=True, name="process_image", max_retries=3)
def process_image(self, image_id: str):
    """
    Full image processing pipeline:
    1. Download from MinIO
    2. Extract metadata + EXIF
    3. Generate thumbnail
    4. Compute perceptual hash (for duplicate detection)
    5. Run YOLO object detection
    6. Save all results to MongoDB
    """
    db = get_db()

    try:
        logger.info(f"[{image_id}] Starting processing...")

        # Mark as processing
        db.images.update_one(
            {"_id": ObjectId(image_id)},
            {"$set": {"status": "processing"}}
        )

        # Load image record
        image_doc = db.images.find_one({"_id": ObjectId(image_id)})
        if not image_doc:
            raise ValueError(f"Image {image_id} not found in database")

        storage_key = image_doc["storage_key"]

        # ── Download from MinIO ───────────────────────────────
        logger.info(f"[{image_id}] Downloading from MinIO: {storage_key}")
        image_data = storage.download_file(storage_key)
        if not image_data:
            raise RuntimeError("Failed to download image from MinIO")

        # ── Open with PIL ─────────────────────────────────────
        image = Image.open(BytesIO(image_data))

        # Convert to RGB if needed (e.g. PNG with alpha channel)
        if image.mode not in ("RGB", "L"):
            image = image.convert("RGB")

        # ── Metadata ──────────────────────────────────────────
        metadata = {
            "width": image.width,
            "height": image.height,
            "format": image.format or "JPEG",
            "mode": image.mode,
            "size_bytes": len(image_data),
            "exif": _extract_clean_exif(image),
        }

        # ── Thumbnail ─────────────────────────────────────────
        thumbnail = image.copy()
        thumbnail.thumbnail((400, 400), Image.Resampling.LANCZOS)
        thumb_buffer = BytesIO()
        thumbnail.save(thumb_buffer, format="JPEG", quality=85, optimize=True)
        thumb_data = thumb_buffer.getvalue()

        thumb_key = f"thumbnails/{storage_key}"
        storage.upload_file(thumb_data, thumb_key, "image/jpeg")
        logger.info(f"[{image_id}] Thumbnail uploaded")

        # ── Write to temp file for YOLO + pHash ───────────────
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
            image.save(tmp, format="JPEG")
            tmp_path = tmp.name

        try:
            # pHash (perceptual hash for duplicate detection)
            logger.info(f"[{image_id}] Computing pHash...")
            phash = compute_phash(tmp_path)

            # YOLO detection
            logger.info(f"[{image_id}] Running YOLO detection...")
            detections = detector.detect_objects(tmp_path)
            unique_labels = detector.extract_unique_labels(detections)
            logger.info(f"[{image_id}] YOLO found {len(unique_labels)} unique labels")

        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

        # ── Build tag documents ───────────────────────────────
        tag_docs = [
            {
                "tag_name": item["label"],
                "confidence": round(item["confidence"], 4),
                "source": "yolo",
            }
            for item in unique_labels
        ]
        tag_strings = [t["tag_name"].lower() for t in tag_docs]

        # ── Save to MongoDB ───────────────────────────────────
        result = db.images.update_one(
            {"_id": ObjectId(image_id)},
            {
                "$set": {
                    "metadata": metadata,
                    "phash": phash,
                    "thumbnail_key": thumb_key,
                    "tags": tag_docs,
                    "tag_strings": tag_strings,
                    "status": "completed",
                    "processed_at": datetime.utcnow(),
                    "error": None,
                }
            },
        )

        logger.info(
            f"[{image_id}] ✓ Done — {len(tag_docs)} tags: {tag_strings[:8]}"
            f" (modified: {result.modified_count})"
        )

        return {
            "status": "success",
            "image_id": image_id,
            "tags_count": len(tag_docs),
            "tags": tag_strings[:10],
        }

    except Exception as exc:
        logger.exception(f"[{image_id}] ✗ Processing failed: {exc}")
        db.images.update_one(
            {"_id": ObjectId(image_id)},
            {
                "$set": {
                    "status": "failed",
                    "error": str(exc),
                    "processed_at": datetime.utcnow(),
                }
            },
        )
        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)