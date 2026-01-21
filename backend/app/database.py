from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import ASCENDING, TEXT
from app.config import settings
import logging
from typing import Optional, Any

logger = logging.getLogger(__name__)

class Database:
    client: Optional[Any] = None
    db: Optional[Any] = None

db = Database()

async def connect_to_mongo():
    """Connect to MongoDB"""
    try:
        logger.info(f"Connecting to MongoDB at {settings.MONGODB_URL}")

        db.client = AsyncIOMotorClient(
            settings.MONGODB_URL,
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=10000,
        )

        # Test connection
        await db.client.admin.command("ping")
        logger.info("MongoDB connection successful")

        if not settings.MONGODB_DB:
            raise ValueError("MONGODB_DB is not set in environment variables")

        db.db = db.client[settings.MONGODB_DB]
        logger.info(f"Database '{settings.MONGODB_DB}' selected")

        await create_indexes()

    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        raise


async def close_mongo_connection():
    """Close MongoDB connection"""
    try:
        if db.client is not None:
            db.client.close()
            logger.info("MongoDB connection closed")
    except Exception as e:
        logger.error(f"Error closing MongoDB connection: {e}")


async def create_indexes():
    """Create database indexes"""
    try:
        if db.db is None:
            logger.warning("Database not initialized, cannot create indexes.")
            return

        # Users collection indexes
        await db.db.users.create_index("email", unique=True)
        logger.info("Created index: users.email")

        # Images collection indexes
        await db.db.images.create_index("user_id")
        await db.db.images.create_index("phash")
        
        # FIX: Drop old incorrect text index and create correct one
        try:
            # Drop the old index if it exists
            await db.db.images.drop_index("tags_text")
            logger.info("Dropped old 'tags_text' index")
        except Exception:
            pass  # Index might not exist
        
        try:
            # Create text index on tag_strings field for search
            await db.db.images.create_index([("tag_strings", TEXT)])
            logger.info("Created text index on images.tag_strings")
        except Exception as e:
            # If index already exists with correct name, that's fine
            if "already exists" not in str(e).lower():
                logger.warning(f"Text index note: {e}")
        
        # Additional indexes for better performance
        await db.db.images.create_index("status")
        await db.db.images.create_index("created_at")
        logger.info("Created indexes for images collection")

        # Albums collection indexes
        await db.db.albums.create_index("user_id")
        logger.info("Created index: albums.user_id")
        
        # Album images junction table
        await db.db.album_images.create_index([("album_id", ASCENDING), ("image_id", ASCENDING)], unique=True)
        logger.info("Created compound index on album_images")

    except Exception as e:
        logger.error(f"Error creating indexes: {e}")


def get_database() -> Any:
    """Return the active database instance"""
    if db.db is None:
        raise RuntimeError("Database not connected. Call connect_to_mongo() first.")
    return db.db