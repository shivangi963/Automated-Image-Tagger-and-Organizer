from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import connect_to_mongo, close_mongo_connection
from app.routers import auth, images, albums, search
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.API_VERSION,
    description="Automated Image Tagger and Organizer with YOLO, MinIO, and MongoDB"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    logger.info("Starting application...")
    await connect_to_mongo()
    logger.info("Application started successfully")


# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down application...")
    await close_mongo_connection()
    logger.info("Application shut down successfully")


# Health check endpoint
@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "message": "Image Tagger and Organizer API",
        "version": settings.API_VERSION,
        "status": "healthy"
    }


# Include routers
app.include_router(auth.router)
app.include_router(images.router)
app.include_router(albums.router)
app.include_router(search.router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)