import logging
from celery_worker import celery_app
from app.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Test Celery connection
try:
    # Check broker connection
    conn = celery_app.connection()
    conn.connect()
    logger.info("✅ Celery broker connection successful")
    conn.release()
    
    # Check if tasks are registered
    registered_tasks = list(celery_app.tasks.keys())
    logger.info(f"✅ Registered tasks: {registered_tasks}")
    
    if 'process_image' in registered_tasks:
        logger.info("✅ process_image task is registered")
    else:
        logger.error("❌ process_image task NOT found!")
    
    # Inspect workers
    inspect = celery_app.control.inspect()
    active_workers = inspect.active()
    
    if active_workers:
        logger.info(f"✅ Active Celery workers: {list(active_workers.keys())}")
    else:
        logger.error("❌ No active Celery workers found!")
        
except Exception as e:
    logger.error(f"❌ Celery connection failed: {e}")
    print("\nMake sure Redis and Celery worker are running!")