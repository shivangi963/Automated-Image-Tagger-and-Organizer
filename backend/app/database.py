"""
Database Module for Automated Image Tagger and Organizer
VTU Mini Project - Bangalore College of Engineering & Technology
Team: Shivangi Shukla, Aliya Aiman, Anamika Kumari
"""

from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import ASCENDING, TEXT, DESCENDING
from pymongo.errors import CollectionInvalid
from app.config import settings
import logging

logger = logging.getLogger(__name__)


class Database:
    """MongoDB Atlas Database Connection Handler"""
    client = None
    db = None


db = Database()


async def connect_to_mongo():
    """
    Connect to MongoDB Atlas cloud database
    Implements connection pooling for optimal performance
    """
    try:
        logger.info("=" * 60)
        logger.info("Connecting to MongoDB Atlas Cloud Database...")
        logger.info(f"Project: {settings.PROJECT_NAME}")
        logger.info(f"Institution: {settings.INSTITUTION}")
        logger.info("=" * 60)
        
        # Create client with MongoDB Atlas connection string
        db.client = AsyncIOMotorClient(
            settings.MONGODB_URI,
            maxPoolSize=50,  # Maximum concurrent connections
            minPoolSize=10,  # Minimum connections to maintain
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=10000,
            socketTimeoutMS=10000,
            retryWrites=True,
            w='majority'  # Write concern for data durability
        )
        
        # Get database name from URI or use default
        db.db = db.client[settings.database_name]
        
        # Verify connection by pinging
        await db.client.admin.command('ping')
        logger.info(f"✓ Successfully connected to database: {settings.database_name}")
        
        # Get server info
        server_info = await db.client.server_info()
        logger.info(f"✓ MongoDB version: {server_info.get('version')}")
        
        # Create collections and indexes
        await ensure_collections()
        await create_indexes()
        
        logger.info("✓ Database initialization complete")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"✗ Failed to connect to MongoDB Atlas: {e}")
        logger.error("Please check your connection string and network connectivity")
        raise


async def close_mongo_connection():
    """Close MongoDB connection gracefully"""
    logger.info("Closing MongoDB Atlas connection...")
    if db.client:
        db.client.close()
    logger.info("✓ MongoDB connection closed")


async def ensure_collections():
    """
    Create required collections if they don't exist
    Following the project architecture from the PDF
    """
    collections = [
        'users',           # User accounts
        'images',          # Image metadata
        'tags',            # Tag definitions
        'image_tags',      # Image-Tag relationships
        'albums',          # Photo albums
        'album_images',    # Album-Image relationships
        'ocr_text',        # Extracted text from images
        'processing_jobs'  # Background job tracking
    ]
    
    existing = await db.db.list_collection_names()
    
    for collection in collections:
        if collection not in existing:
            try:
                await db.db.create_collection(collection)
                logger.info(f"✓ Created collection: {collection}")
            except CollectionInvalid:
                pass  # Collection already exists
    
    logger.info(f"✓ All {len(collections)} collections verified")


async def create_indexes():
    """
    Create optimized database indexes for fast queries
    Implements search functionality as per project requirements
    """
    
    try:
        # Users collection - Authentication
        await db.db.users.create_index(
            [("email", ASCENDING)], 
            unique=True, 
            background=True,
            name="idx_users_email"
        )
        await db.db.users.create_index(
            [("created_at", DESCENDING)], 
            background=True,
            name="idx_users_created"
        )
        
        # Images collection - Core functionality
        await db.db.images.create_index(
            [("user_id", ASCENDING), ("created_at", DESCENDING)], 
            background=True,
            name="idx_images_user_date"
        )
        await db.db.images.create_index(
            [("user_id", ASCENDING), ("status", ASCENDING)], 
            background=True,
            name="idx_images_user_status"
        )
        await db.db.images.create_index(
            [("status", ASCENDING)], 
            background=True,
            name="idx_images_status"
        )
        await db.db.images.create_index(
            [("phash", ASCENDING)], 
            background=True,
            name="idx_images_phash"
        )
        await db.db.images.create_index(
            [("storage_key", ASCENDING)], 
            background=True,
            name="idx_images_storage"
        )
        
        # Tags collection - Search functionality
        await db.db.tags.create_index(
            [("name", TEXT)], 
            background=True,
            name="idx_tags_text_search"
        )
        await db.db.tags.create_index(
            [("name", ASCENDING)], 
            unique=True, 
            background=True,
            name="idx_tags_name"
        )
        await db.db.tags.create_index(
            [("source", ASCENDING)], 
            background=True,
            name="idx_tags_source"
        )
        
        # Image_tags junction - Fast tag lookups
        await db.db.image_tags.create_index(
            [("image_id", ASCENDING)], 
            background=True,
            name="idx_image_tags_image"
        )
        await db.db.image_tags.create_index(
            [("tag_id", ASCENDING)], 
            background=True,
            name="idx_image_tags_tag"
        )
        await db.db.image_tags.create_index(
            [("image_id", ASCENDING), ("tag_id", ASCENDING)], 
            unique=True, 
            background=True,
            name="idx_image_tags_unique"
        )
        await db.db.image_tags.create_index(
            [("confidence", DESCENDING)], 
            background=True,
            name="idx_image_tags_confidence"
        )
        
        # Albums collection - Organization
        await db.db.albums.create_index(
            [("user_id", ASCENDING), ("created_at", DESCENDING)], 
            background=True,
            name="idx_albums_user_date"
        )
        await db.db.albums.create_index(
            [("name", TEXT)], 
            background=True,
            name="idx_albums_text_search"
        )
        
        # Album_images junction
        await db.db.album_images.create_index(
            [("album_id", ASCENDING)], 
            background=True,
            name="idx_album_images_album"
        )
        await db.db.album_images.create_index(
            [("image_id", ASCENDING)], 
            background=True,
            name="idx_album_images_image"
        )
        await db.db.album_images.create_index(
            [("album_id", ASCENDING), ("image_id", ASCENDING)], 
            unique=True, 
            background=True,
            name="idx_album_images_unique"
        )
        
        # OCR text - Text extraction search
        await db.db.ocr_text.create_index(
            [("image_id", ASCENDING)], 
            background=True,
            name="idx_ocr_image"
        )
        await db.db.ocr_text.create_index(
            [("content", TEXT)], 
            background=True,
            name="idx_ocr_text_search"
        )
        
        # Processing jobs - Task queue
        await db.db.processing_jobs.create_index(
            [("image_id", ASCENDING)], 
            background=True,
            name="idx_jobs_image"
        )
        await db.db.processing_jobs.create_index(
            [("status", ASCENDING), ("created_at", DESCENDING)], 
            background=True,
            name="idx_jobs_status_date"
        )
        
        logger.info("✓ All database indexes created successfully")
        
    except Exception as e:
        logger.warning(f"Index creation warning: {e}")


async def get_database_stats():
    """Get database statistics for monitoring"""
    try:
        stats = await db.db.command("dbStats")
        return {
            "database": stats.get("db"),
            "collections": stats.get("collections"),
            "objects": stats.get("objects"),
            "data_size_mb": round(stats.get("dataSize", 0) / (1024 * 1024), 2),
            "storage_size_mb": round(stats.get("storageSize", 0) / (1024 * 1024), 2),
            "indexes": stats.get("indexes"),
            "index_size_mb": round(stats.get("indexSize", 0) / (1024 * 1024), 2)
        }
    except Exception as e:
        logger.error(f"Failed to get database stats: {e}")
        return None


async def get_collection_counts():
    """Get document counts for all collections"""
    try:
        counts = {}
        collections = ['users', 'images', 'tags', 'albums', 'processing_jobs']
        
        for collection in collections:
            counts[collection] = await db.db[collection].count_documents({})
        
        return counts
    except Exception as e:
        logger.error(f"Failed to get collection counts: {e}")
        return {}


def get_database():
    """Dependency to get database instance"""
    return db.db