from celery import Celery
from app.config import settings


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

if __name__ == '__main__':
    celery_app.start()