from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import ASCENDING, TEXT
from app.config import settings
import logging

logger = logging.getLogger(__name__)


class Database:
    client: AsyncIOMotorClient = None
    db: AsyncIOMotorDatabase = None


db = Database()


async def connect_to_mongo():
    """Connect to MongoDB"""
    try:
        logger.info(f"Connecting to MongoDB at {settings.MONGODB_URL}")
        
        db.client = AsyncIOMotorClient(
            settings.MONGODB_URL,
            serverSelectionTimeoutMS=5000,  # 5 second timeout
            connectTimeoutMS=10000,
        )
        
        # Test connection
        await db.client.admin.command('ping')
        logger.info("✓ MongoDB connection successful")
        
        db.db = db.client[settings.MONGODB_DB]
        logger.info(f"✓ Database '{settings.MONGODB_DB}' selected")
        
        # Create indexes
        await create_indexes()
        
    except Exception as e:
        logger.error(f"✗ Failed to connect to MongoDB: {e}")
        raise


async def close_mongo_connection():
    """Close MongoDB connection"""
    try:
        if db.client:
            db.client.close()
            logger.info("✓ MongoDB connection closed")
    except Exception as e:
        logger.error(f"✗ Error closing MongoDB connection: {e}")


async def create_indexes():
    """Create database indexes"""
    try:
        if not db.db:
            logger.warning("Database not initialized")
            return
        
        # Users collection indexes
        await db.db.users.create_index("email", unique=True)
        logger.info("✓ Created index: users.email")
        
        # Images collection indexes
        await db.db.images.create_index("user_id")
        await db.db.images.create_index("phash")
        await db.db.images.create_index([("tags", TEXT)])
        logger.info("✓ Created indexes: images")
        
        # Albums collection indexes
        await db.db.albums.create_index("user_id")
        logger.info("✓ Created indexes: albums")
        
    except Exception as e:
        logger.error(f"✗ Error creating indexes: {e}")


def get_database() -> AsyncIOMotorDatabase:
    """Get database instance"""
    if not db.db:
        raise RuntimeError("Database not connected. Call connect_to_mongo() first.")
    return db.db