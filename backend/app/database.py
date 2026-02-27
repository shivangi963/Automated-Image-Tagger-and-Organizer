from motor.motor_asyncio import AsyncIOMotorClient
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
    """Connect to MongoDB and create indexes."""
    url = settings.MONGODB_URL

    safe_url = url
    if "@" in url:
        safe_url = url.split("@")[-1]   
    logger.info(f"Connecting to MongoDB at ...@{safe_url}")

    try:
        db.client = AsyncIOMotorClient(
            url,
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=10000,
        )
        # Verify the connection works
        await db.client.admin.command("ping")
        logger.info("MongoDB connection successful")

        db.db = db.client[settings.MONGODB_DB]
        logger.info(f" Using database: '{settings.MONGODB_DB}'")

        await create_indexes()

    except Exception as e:
        error_msg = str(e)
        logger.error(f"MongoDB connection failed: {error_msg}")

        # Give actionable hints
        if "Authentication failed" in error_msg or "auth" in error_msg.lower():
            logger.error(
                "  → AUTH ERROR. Your MONGODB_URL has wrong credentials."
            )
        elif "Connection refused" in error_msg or "timed out" in error_msg.lower():
            logger.error(
                "  → CONNECTION REFUSED. MongoDB is not running."
            )
        raise


async def close_mongo_connection():
    """Close MongoDB connection."""
    try:
        if db.client is not None:
            db.client.close()
            logger.info("MongoDB connection closed")
    except Exception as e:
        logger.error(f"Error closing MongoDB connection: {e}")


async def create_indexes():
    """Create all required indexes."""
    try:
        if db.db is None:
            logger.warning("Database not initialized, skipping index creation.")
            return

        # users
        await db.db.users.create_index("email", unique=True)

        # images
        await db.db.images.create_index("user_id")
        await db.db.images.create_index("phash")
        await db.db.images.create_index("status")
        await db.db.images.create_index("created_at")

        # Text index on tag_strings (drop old one first if it exists with wrong name)
        try:
            await db.db.images.drop_index("tags_text")
        except Exception:
            pass
        try:
            await db.db.images.create_index([("tag_strings", TEXT)])
        except Exception as e:
            if "already exists" not in str(e).lower():
                logger.warning(f"Text index note: {e}")

        # albums
        await db.db.albums.create_index("user_id")

        # album_images junction
        await db.db.album_images.create_index(
            [("album_id", ASCENDING), ("image_id", ASCENDING)], unique=True
        )

        logger.info(" All MongoDB indexes created/verified")

    except Exception as e:
        logger.error(f"Error creating indexes: {e}")


def get_database() -> Any:
    """Return the active database instance."""
    if db.db is None:
        raise RuntimeError(
            "Database not connected. "
            "Make sure connect_to_mongo() completed successfully."
        )
    return db.db