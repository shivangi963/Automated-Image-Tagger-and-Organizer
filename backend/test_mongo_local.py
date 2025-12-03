"""
Test Local MongoDB Connection
Run this to verify MongoDB is working properly
"""

import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MONGODB_URL = "mongodb://localhost:27017"
MONGODB_DB = "image_tagger"


async def test_connection():
    """Test MongoDB connection"""
    print("=" * 60)
    print("Testing Local MongoDB Connection...")
    print("=" * 60)
    
    try:
        # Connect
        logger.info(f"Attempting to connect to {MONGODB_URL}")
        client = AsyncIOMotorClient(
            MONGODB_URL,
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=10000,
        )
        
        # Test connection
        await client.admin.command('ping')
        logger.info("✓ Connection successful!")
        
        # Get database
        db = client[MONGODB_DB]
        logger.info(f"✓ Database '{MONGODB_DB}' selected")
        
        # List collections
        collections = await db.list_collection_names()
        logger.info(f"✓ Collections: {collections if collections else 'None yet'}")
        
        # Create a test collection
        logger.info("Creating test collection...")
        await db.test_collection.insert_one({"message": "Test", "status": "OK"})
        logger.info("✓ Test document inserted")
        
        # Read test collection
        doc = await db.test_collection.find_one()
        logger.info(f"✓ Retrieved test document: {doc}")
        
        # Clean up
        await db.test_collection.delete_many({})
        logger.info("✓ Test collection cleaned up")
        
        # Server info
        server_info = await client.server_info()
        logger.info(f"✓ MongoDB Version: {server_info.get('version')}")
        
        client.close()
        logger.info("✓ Connection closed")
        
        print("=" * 60)
        print("✓ ALL TESTS PASSED - MongoDB is working!")
        print("=" * 60)
        
    except Exception as e:
        print("=" * 60)
        print(f"✗ ERROR: {e}")
        print("=" * 60)
        logger.error(f"Connection failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(test_connection())