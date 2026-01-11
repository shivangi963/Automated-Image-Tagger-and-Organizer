import sys
import os

print("=" * 60)
print("CHECKING APP CONFIGURATION")
print("=" * 60)

# Add current directory to Python path
sys.path.insert(0, os.getcwd())

try:
    # Try to import your app's settings
    from app.config import settings
    
    print(f"✓ Successfully imported settings from app.config")
    print(f"\n1. MONGODB_URL from settings: {settings.MONGODB_URL}")
    print(f"2. MONGODB_DB from settings: {settings.MONGODB_DB}")
    
    # Check if it contains old credentials
    if 'myUser' in settings.MONGODB_URL or 'myPassword' in settings.MONGODB_URL:
        print(f"\n⚠ PROBLEM: Settings still using OLD authentication URL!")
        print(f"   Should be: mongodb://localhost:27017")
    else:
        print(f"\n✓ Settings using correct URL (no authentication)")
    
    # Test the connection with app's actual URL
    print(f"\n3. Testing connection with app's URL...")
    from pymongo import MongoClient
    
    try:
        client = MongoClient(settings.MONGODB_URL, serverSelectionTimeoutMS=3000)
        result = client.admin.command('ping')
        print(f"   ✓ Connection successful: {result}")
        
        # Check databases
        dbs = client.list_database_names()
        print(f"   ✓ Databases found: {len(dbs)}")
        
    except Exception as e:
        print(f"   ✗ Connection failed: {e}")
        
except ImportError as e:
    print(f"✗ Cannot import app.config: {e}")
    print(f"   Make sure you're in the correct directory")
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("If settings show OLD URL, check these files:")
print("1. .env file in current directory")
print("2. app/config.py for default values")
print("=" * 60)