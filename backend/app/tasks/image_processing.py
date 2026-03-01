"""
Full image processing pipeline:
  1. Download from MinIO
  2. Extract metadata + EXIF
  3. Generate thumbnail
  4. Compute perceptual hash  (duplicate detection)
  5. YOLO object detection    (person, car, dog …)
  6. BLIP scene captioning   (natural-language description)
  7. CLIP scene tagging      (beach, sky, indoor …)
  8. EasyOCR text extraction (signs, labels, printed text)
  9. Persist everything to MongoDB
"""

from celery_worker import celery_app
from app.storage import storage
from app.ml.yolo_detector import detector
from app.ml.scene_tagger import scene_tagger
from app.ml.ocr import ocr_extractor
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


def get_sync_db():
    """Synchronous MongoDB connection for Celery tasks."""
    client = MongoClient(
        settings.MONGODB_URL,
        serverSelectionTimeoutMS=5000,
    )
    return client[settings.MONGODB_DB]


def _extract_clean_exif(image: Image.Image) -> dict:
    """Return only JSON-serialisable EXIF values."""
    try:
        raw = image._getexif()
        if not raw:
            return {}
        return {
            str(k): v
            for k, v in raw.items()
            if isinstance(v, (str, int, float, bool))
        }
    except Exception:
        return {}


def _merge_tags(
    yolo_labels: list,
    caption_tags: list,
    scene_tags: list,
    ocr_full_text: str,
) -> tuple[list, list]:
    """
    Combine tags from all sources into:
      - tag_docs  : list of {"tag_name", "confidence", "source"}
      - tag_strings: deduplicated lowercased list for MongoDB text index
    """
    seen = {}  # tag_name → best confidence

    # ── YOLO objects ──────────────────────────────────────────────────────────
    for item in yolo_labels:
        name = item["label"].lower().strip()
        conf = item["confidence"]
        if name not in seen or conf > seen[name][0]:
            seen[name] = (conf, "yolo")

    # ── BLIP caption keywords ─────────────────────────────────────────────────
    for word in caption_tags:
        name = word.lower().strip()
        if len(name) < 3:
            continue
        if name not in seen:
            seen[name] = (0.75, "blip_caption")

    # ── CLIP scene tags ───────────────────────────────────────────────────────
    for item in scene_tags:
        # CLIP tags can be multi-word ("blue sky") — keep as-is
        name = item["label"].lower().strip()
        conf = item["confidence"]
        if name not in seen or conf > seen[name][0]:
            seen[name] = (conf, "clip_scene")

    # ── OCR text as tags (individual words) ───────────────────────────────────
    if ocr_full_text:
        for word in ocr_full_text.lower().split():
            word = word.strip(".,!?;:'\"()")
            if len(word) >= 3 and word.isalpha():
                if word not in seen:
                    seen[word] = (0.9, "ocr")

    tag_docs = [
        {"tag_name": name, "confidence": round(conf, 4), "source": src}
        for name, (conf, src) in seen.items()
    ]
    tag_docs.sort(key=lambda x: x["confidence"], reverse=True)

    tag_strings = list(seen.keys())

    return tag_docs, tag_strings


@celery_app.task(bind=True, name="process_image", max_retries=3)
def process_image(self, image_id: str):
    db = get_sync_db()

    try:
        logger.info(f"[{image_id}] ─── Starting pipeline ───")

        db.images.update_one(
            {"_id": ObjectId(image_id)},
            {"$set": {"status": "processing"}},
        )

        image_doc = db.images.find_one({"_id": ObjectId(image_id)})
        if not image_doc:
            raise ValueError(f"Image {image_id} not found")

        storage_key = image_doc["storage_key"]

        # ── 1. Download ───────────────────────────────────────────────────────
        logger.info(f"[{image_id}] Downloading from MinIO…")
        image_data = storage.download_file(storage_key)
        if not image_data:
            raise RuntimeError("Failed to download image from MinIO")

        # ── 2. Open with PIL ──────────────────────────────────────────────────
        image = Image.open(BytesIO(image_data))
        if image.mode not in ("RGB", "L"):
            image = image.convert("RGB")

        # ── 3. Metadata ───────────────────────────────────────────────────────
        metadata = {
            "width": image.width,
            "height": image.height,
            "format": image.format or "JPEG",
            "mode": image.mode,
            "size_bytes": len(image_data),
            "exif": _extract_clean_exif(image),
        }

        # ── 4. Thumbnail ──────────────────────────────────────────────────────
        thumbnail = image.copy()
        thumbnail.thumbnail((400, 400), Image.Resampling.LANCZOS)
        buf = BytesIO()
        thumbnail.save(buf, format="JPEG", quality=85, optimize=True)
        thumb_key = f"thumbnails/{storage_key}"
        storage.upload_file(buf.getvalue(), thumb_key, "image/jpeg")
        logger.info(f"[{image_id}] Thumbnail uploaded")

        # ── Write to temp file (shared by YOLO, pHash, OCR) ──────────────────
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
            image.save(tmp, format="JPEG")
            tmp_path = tmp.name

        try:
            # ── 5. pHash ──────────────────────────────────────────────────────
            logger.info(f"[{image_id}] Computing pHash…")
            phash = compute_phash(tmp_path)

            # ── 6. YOLO object detection ──────────────────────────────────────
            logger.info(f"[{image_id}] Running YOLO…")
            detections   = detector.detect_objects(tmp_path)
            yolo_labels  = detector.extract_unique_labels(detections)
            logger.info(f"[{image_id}] YOLO → {len(yolo_labels)} objects")

            # ── 7. BLIP + CLIP scene/content tagging ──────────────────────────
            logger.info(f"[{image_id}] Running BLIP captioning + CLIP scene tagging…")
            scene_result = scene_tagger.tag_image(image)
            caption      = scene_result.get("caption", "")
            caption_tags = scene_result.get("caption_tags", [])
            clip_scenes  = scene_result.get("scene_tags", [])
            logger.info(f"[{image_id}] Caption: '{caption}'")
            logger.info(f"[{image_id}] CLIP scenes: {[t['label'] for t in clip_scenes[:5]]}")

            # ── 8. OCR ────────────────────────────────────────────────────────
            logger.info(f"[{image_id}] Running OCR…")
            ocr_result   = ocr_extractor.extract_text(tmp_path)
            ocr_text     = ocr_result.get("full_text", "")
            ocr_regions  = ocr_result.get("regions", [])
            if ocr_text:
                logger.info(f"[{image_id}] OCR found text: '{ocr_text[:100]}'")

        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

        # ── 9. Merge all tags ─────────────────────────────────────────────────
        tag_docs, tag_strings = _merge_tags(
            yolo_labels, caption_tags, clip_scenes, ocr_text
        )

        logger.info(
            f"[{image_id}] Total unique tags: {len(tag_docs)} "
            f"— sample: {tag_strings[:8]}"
        )

        # ── 10. Persist to MongoDB ────────────────────────────────────────────
        db.images.update_one(
            {"_id": ObjectId(image_id)},
            {
                "$set": {
                    "metadata": metadata,
                    "phash": phash,
                    "thumbnail_key": thumb_key,
                    "tags": tag_docs,
                    "tag_strings": tag_strings,
                    # Rich caption + OCR stored separately for future search
                    "caption": caption,
                    "ocr_text": ocr_text,
                    "ocr_regions": ocr_regions,
                    "status": "completed",
                    "processed_at": datetime.utcnow(),
                    "error": None,
                }
            },
        )

        logger.info(f"[{image_id}] ✓ Pipeline complete")

        return {
            "status": "success",
            "image_id": image_id,
            "tags_count": len(tag_docs),
            "has_ocr": bool(ocr_text),
            "caption": caption,
            "tags_sample": tag_strings[:10],
        }

    except Exception as exc:
        logger.exception(f"[{image_id}] ✗ Pipeline failed: {exc}")
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
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)