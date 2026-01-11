import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from app.config import settings

async def migrate_tags():
    client = AsyncIOMotorClient(settings.MONGODB_URL)
    db = client[settings.MONGODB_DB]
    
    # Get all images
    images = await db.images.find({}).to_list(None)
    
    for img in images:
        # If tags field doesn't exist, initialize it
        if "tags" not in img:
            await db.images.update_one(
                {"_id": img["_id"]},
                {"$set": {"tags": [], "tag_strings": []}}
            )
            print(f"Fixed: {img.get('original_filename')}")
    
    print("Migration complete!")
    client.close()

if __name__ == "__main__":
    asyncio.run(migrate_tags())