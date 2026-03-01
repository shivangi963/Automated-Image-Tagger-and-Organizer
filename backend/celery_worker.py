from celery import Celery
from celery.signals import worker_ready
from app.config import settings
import logging

logger = logging.getLogger(__name__)

# Create Celery app
celery_app = Celery(
    "image_tagger",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

# Configuration
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,  # 5 minutes
    worker_prefetch_multiplier=1,
    imports=('app.tasks.image_processing',)
)

from app.tasks import image_processing


@worker_ready.connect
def preload_models(sender, **kwargs):
    """
    Pre-load all ML models as soon as the Celery worker is ready.
    This runs once at startup so the FIRST uploaded image processes
    at full speed instead of waiting for lazy model downloads/loads.
    """
    logger.info("⏳ Pre-loading ML models (YOLO, BLIP, CLIP, EasyOCR)…")

    try:
        from app.ml.yolo_detector import detector
        detector._load_model()
        logger.info("✓ YOLO ready")
    except Exception as e:
        logger.error(f"✗ YOLO pre-load failed: {e}")

    try:
        from app.ml.scene_tagger import scene_tagger
        from PIL import Image
        import io
        # Load both BLIP and CLIP by running a tiny dummy image through the tagger
        dummy = Image.new("RGB", (32, 32), color=(128, 128, 128))
        scene_tagger._load_blip()
        logger.info("✓ BLIP ready")
        scene_tagger._load_clip()
        logger.info("✓ CLIP ready")
    except Exception as e:
        logger.error(f"✗ BLIP/CLIP pre-load failed: {e}")

    try:
        from app.ml.ocr import ocr_extractor
        ocr_extractor._load_reader()
        logger.info("✓ EasyOCR ready")
    except Exception as e:
        logger.error(f"✗ EasyOCR pre-load failed: {e}")

    logger.info("🚀 All ML models loaded — worker is ready")


if __name__ == '__main__':
    celery_app.start()