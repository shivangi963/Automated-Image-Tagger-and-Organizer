from pymongo import MongoClient
import time
import sys
import os

print("=" * 60)
print("FINAL MONGODB CONNECTION TEST")
print("=" * 60)

try:
    # Add current directory to Python path
    sys.path.insert(0, os.getcwd())
    
    # Import app settings
    from app.config import settings
    print(f"1. App MONGODB_URL: {settings.MONGODB_URL}")
    
    # Check URL format
    if '@' in settings.MONGODB_URL and 'localhost' in settings.MONGODB_URL:
        print("   ⚠ WARNING: URL contains credentials (@ symbol)")
        print("   Should be: mongodb://localhost:27017")
    else:
        print("   ✓ URL format looks good (no credentials)")
    
    # Test connection
    print(f"\n2. Testing connection...")
    client = MongoClient(settings.MONGODB_URL, serverSelectionTimeoutMS=5000)
    
    # Ping test
    ping_result = client.admin.command('ping')
    print(f"   ✓ Ping: {ping_result}")
    
    # List databases test
    dbs = client.list_database_names()
    print(f"   ✓ Can list {len(dbs)} databases")
    
    # Access image_tagger
    db = client['image_tagger']
    collections = db.list_collection_names()
    print(f"   ✓ Can access 'image_tagger' database")
    print(f"   Collections: {collections}")
    
    print("\n" + "=" * 60)
    print("✅ SUCCESS: MongoDB is ready for your application!")
    print("=" * 60)
    
except ImportError as e:
    print(f"✗ Cannot import app.config: {e}")
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("If authentication error, check:")
    print("1. MongoDB is running with --noauth")
    print("2. .env file has: MONGODB_URL=mongodb://localhost:27017")
    print("=" * 60)