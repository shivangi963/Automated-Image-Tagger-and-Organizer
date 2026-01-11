from pymongo import MongoClient
import time

print("=" * 60)
print("Testing MongoDB Connection")
print("=" * 60)

for attempt in range(3):
    print(f"\nAttempt {attempt + 1}/3")
    try:
        # Try to connect
        client = MongoClient('mongodb://localhost:27017', serverSelectionTimeoutMS=3000)
        
        # Send a ping
        result = client.admin.command('ping')
        print(f"✓ Ping successful: {result}")
        
        # List databases
        databases = client.list_database_names()
        print(f"✓ Found databases: {databases}")
        
        # Check image_tagger
        if 'image_tagger' in databases:
            print("✓ Database 'image_tagger' exists")
        else:
            print("• Database 'image_tagger' doesn't exist yet (will be created automatically)")
            
        # Try to access it
        db = client['image_tagger']
        collections = db.list_collection_names()
        print(f"✓ Collections in image_tagger: {collections}")
        
        print("\n" + "=" * 60)
        print("✓ SUCCESS: MongoDB is ready for your application!")
        print("=" * 60)
        
        break
        
    except Exception as e:
        print(f"✗ Attempt failed: {e}")
        if attempt < 2:
            print("Waiting 2 seconds before retry...")
            time.sleep(2)
        else:
            print("\n" + "=" * 60)
            print("✗ FAILED: Could not connect to MongoDB")
            print("Make sure MongoDB is running in another window with:")
            print(r'  .\mongod.exe --dbpath "C:\data\db" --noauth')
            print("=" * 60)