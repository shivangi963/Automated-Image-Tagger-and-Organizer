import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from app.config import settings

async def fix_all():
    """Fix indexes and reset images for reprocessing"""
    client = AsyncIOMotorClient(settings.MONGODB_URL)
    db = client[settings.MONGODB_DB]
    
    print("=" * 70)
    print("FIXING ALL ISSUES")
    print("=" * 70)
    
    # 1. Fix text index
    print("\n1. Fixing text search index...")
    try:
        await db.images.drop_index("tags_text")
        print("   ✅ Dropped old 'tags_text' index")
    except Exception as e:
        print(f"   ⚠️  Old index may not exist: {e}")
    
    try:
        await db.images.create_index([("tag_strings", "text")])
        print("   ✅ Created new 'tag_strings' text index")
    except Exception as e:
        print(f"   ⚠️  Index creation: {e}")
    
    # 2. Show current state
    print("\n2. Current database state:")
    total = await db.images.count_documents({})
    completed = await db.images.count_documents({"status": "completed"})
    pending = await db.images.count_documents({"status": "pending"})
    with_tags = await db.images.count_documents({"tags": {"$exists": True, "$ne": []}})
    
    print(f"   Total images: {total}")
    print(f"   Completed: {completed}")
    print(f"   Pending: {pending}")
    print(f"   With tags: {with_tags}")
    
    # 3. Ask user if they want to reset images
    if completed > 0:
        print(f"\n3. Found {completed} completed images.")
        print("   Do you want to reset them for reprocessing? (y/n)")
        choice = input("   > ").strip().lower()
        
        if choice == 'y':
            result = await db.images.update_many(
                {"status": "completed"},
                {
                    "$set": {
                        "status": "pending",
                        "tags": [],
                        "tag_strings": []
                    }
                }
            )
            print(f"   ✅ Reset {result.modified_count} images to pending")
            print("\n   Now restart your Celery worker to reprocess images.")
        else:
            print("   Skipped reset. Existing completed images will keep their current state.")
    else:
        print("\n3. No completed images to reset.")
    
    # 4. List all indexes
    print("\n4. Current indexes on images collection:")
    indexes = await db.images.list_indexes().to_list(None)
    for idx in indexes:
        print(f"   - {idx['name']}: {idx.get('key', {})}")
    
    print("\n" + "=" * 70)
    print("DONE!")
    print("=" * 70)
    
    client.close()

if __name__ == "__main__":
    asyncio.run(fix_all())