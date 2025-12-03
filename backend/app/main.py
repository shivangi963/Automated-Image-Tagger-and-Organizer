from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import connect_to_mongo, close_mongo_connection, create_indexes
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
    debug=settings.DEBUG
)

# CORS middleware - use configured origins from settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(images.router)
app.include_router(albums.router)
app.include_router(search.router)


# Startup event
@app.on_event("startup")
async def startup():
    logger.info("=" * 60)
    logger.info("Starting Automated Image Tagger & Organizer")
    logger.info("=" * 60)
    await connect_to_mongo()
    await create_indexes()
    logger.info("✓ Application startup complete")


# Shutdown event
@app.on_event("shutdown")
async def shutdown():
    logger.info("Shutting down application...")
    await close_mongo_connection()
    logger.info("✓ Application shutdown complete")


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.API_VERSION,
    }


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Welcome to Automated Image Tagger & Organizer",
        "version": settings.API_VERSION,
        "docs": "/docs",
    }