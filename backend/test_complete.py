import sys
import os
import socket

print("=" * 70)
print("COMPLETE DIAGNOSTIC TEST")
print("=" * 70)

# 1. System info
print(f"\n1. SYSTEM INFO:")
print(f"   Current directory: {os.getcwd()}")
print(f"   Python executable: {sys.executable}")
print(f"   Python version: {sys.version}")

# 2. Check MongoDB port
print(f"\n2. CHECKING MONGODB PORT 27017:")
try:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(2)
    result = sock.connect_ex(('localhost', 27017))
    sock.close()
    if result == 0:
        print("   ✓ Port 27017 is OPEN (MongoDB is listening)")
    else:
        print("   ✗ Port 27017 is CLOSED (MongoDB not running)")
except Exception as e:
    print(f"   Error checking port: {e}")

# 3. Check PyMongo installation
print(f"\n3. CHECKING PYMONGO:")
try:
    import pymongo
    print(f"   ✓ PyMongo imported successfully")
    print(f"   Version: {pymongo.__version__}")
    print(f"   Location: {pymongo.__file__}")
except ImportError as e:
    print(f"   ✗ PyMongo import failed: {e}")
    print(f"   This means pymongo is not installed for: {sys.executable}")

# 4. Test MongoDB connection
print(f"\n4. TESTING MONGODB CONNECTION:")
try:
    from pymongo import MongoClient
    print("   Attempting connection to: mongodb://localhost:27017")
    
    client = MongoClient(
        'mongodb://localhost:27017',
        serverSelectionTimeoutMS=5000,
        connectTimeoutMS=5000
    )
    
    # Try ping
    result = client.admin.command('ping')
    print(f"   ✓ MongoDB PING successful: {result}")
    
    # List databases
    databases = client.list_database_names()
    print(f"   ✓ Found {len(databases)} databases")
    print(f"   First few: {databases[:5]}")
    
    client.close()
    
except Exception as e:
    print(f"   ✗ Connection failed: {e}")
    print(f"   Error type: {type(e).__name__}")

print("\n" + "=" * 70)
print("TROUBLESHOOTING:")
print("1. Make sure MongoDB is running with: --noauth")
print("2. You're in 'backend' directory (not parent)")
print("3. Your venv is activated (should see (venv) in prompt)")
print("=" * 70)