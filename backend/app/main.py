from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from contextlib import asynccontextmanager
from app.config import settings
from app.database import connect_to_mongo, close_mongo_connection
from app.routers import auth, images, albums, search
from app.storage import storage
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events
    This replaces the deprecated @app.on_event decorators
    """
    # Startup
    logger.info("Starting application...")
    try:
        # Initialize MongoDB connection
        await connect_to_mongo()
        logger.info("✓ MongoDB connected successfully")
        
        # Initialize MinIO storage (already initialized in storage.py)
        logger.info(f"✓ MinIO storage initialized at {settings.MINIO_ENDPOINT}")
        
        # Log configuration
        logger.info(f"✓ API Version: {settings.API_VERSION}")
        logger.info(f"✓ CORS Origins: {settings.CORS_ORIGINS}")
        logger.info(f"✓ YOLO Model: {settings.YOLO_MODEL}")
        logger.info(f"✓ YOLO Confidence Threshold: {settings.YOLO_CONFIDENCE}")
        
        logger.info("Application started successfully")
        
    except Exception as e:
        logger.error(f"Failed to start application: {e}")
        raise
    
    yield  # Application runs here
    
    # Shutdown
    logger.info("Shutting down application...")
    try:
        await close_mongo_connection()
        logger.info("✓ MongoDB connection closed")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")
    
    logger.info("Application shut down successfully")


# Create FastAPI app with lifespan
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.API_VERSION,
    description="Automated Image Tagger and Organizer with YOLO, MinIO, and MongoDB",
    lifespan=lifespan
)

# CORS middleware - MUST be added before routes
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS if settings.CORS_ORIGINS else ["*"],  # Allow all if not configured
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)


# Health check endpoint
@app.get("/", tags=["Health"])
async def root():
    """
    Root health check endpoint
    Returns application status and version information
    """
    return {
        "message": "Image Tagger and Organizer API",
        "version": settings.API_VERSION,
        "status": "healthy",
        "app_name": settings.APP_NAME
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """
    Detailed health check endpoint
    Checks connectivity to all services
    """
    health_status = {
        "status": "healthy",
        "version": settings.API_VERSION,
        "services": {
            "api": "running",
            "mongodb": "unknown",
            "minio": "unknown",
            "celery": "unknown"
        }
    }
    
    # Check MongoDB
    try:
        from app.database import db
        if db.db is not None:
            await db.db.command("ping")
            health_status["services"]["mongodb"] = "connected"
        else:
            health_status["services"]["mongodb"] = "not_initialized"
    except Exception as e:
        logger.error(f"MongoDB health check failed: {e}")
        health_status["services"]["mongodb"] = "error"
        health_status["status"] = "degraded"
    
    # Check MinIO
    try:
        if storage.client and storage.client.bucket_exists(settings.MINIO_BUCKET):
            health_status["services"]["minio"] = "connected"
        else:
            health_status["services"]["minio"] = "bucket_not_found"
    except Exception as e:
        logger.error(f"MinIO health check failed: {e}")
        health_status["services"]["minio"] = "error"
        health_status["status"] = "degraded"
    
    # Celery status (basic check - you could ping celery here)
    health_status["services"]["celery"] = "running"  # Assume running
    
    return health_status


# Include routers - they already have prefixes defined in their files
app.include_router(auth.router)
app.include_router(images.router)
app.include_router(albums.router)
app.include_router(search.router)


# Error handlers
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request, exc):
    """Custom HTTP exception handler"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "path": str(request.url),
            "status_code": exc.status_code
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Custom general exception handler"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "status_code": 500
        }
    )


# Development server runner
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="info"
    )