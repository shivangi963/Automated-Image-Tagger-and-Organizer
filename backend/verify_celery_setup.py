"""
Run this script to verify Celery setup
Usage: python verify_celery_setup.py
"""
import logging
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.dirname(__file__))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def verify_setup():
    print("=" * 70)
    print("CELERY SETUP VERIFICATION")
    print("=" * 70)
    
    # 1. Check celery_worker.py
    print("\n1. Checking celery_worker.py...")
    try:
        from celery_worker import celery_app
        print(f"   ✅ Celery app created: {celery_app.main}")
        print(f"   ✅ Broker: {celery_app.conf.broker_url}")
        print(f"   ✅ Backend: {celery_app.conf.result_backend}")
        print(f"   ✅ Imports: {celery_app.conf.imports}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False
    
    # 2. Check task file exists
    print("\n2. Checking task file...")
    task_file = "app/tasks/image_processing.py"
    if os.path.exists(task_file):
        print(f"   ✅ Task file exists: {task_file}")
    else:
        print(f"   ❌ Task file missing: {task_file}")
        return False
    
    # 3. Try to import task
    print("\n3. Importing task module...")
    try:
        from app.tasks import image_processing
        print(f"   ✅ Task module imported")
        
        # Check if process_image exists
        if hasattr(image_processing, 'process_image'):
            print(f"   ✅ process_image function found")
        else:
            print(f"   ❌ process_image function NOT found")
            return False
            
    except Exception as e:
        print(f"   ❌ Import error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 4. Check registered tasks
    print("\n4. Checking registered tasks...")
    try:
        conn = celery_app.connection()
        conn.connect()
        print(f"   ✅ Broker connection successful")
        conn.release()
        
        registered = list(celery_app.tasks.keys())
        print(f"   📋 Total registered tasks: {len(registered)}")
        
        # Look for our task
        process_task = None
        for task_name in registered:
            if 'process_image' in task_name:
                process_task = task_name
                break
        
        if process_task:
            print(f"   ✅ Found task: {process_task}")
        else:
            print(f"   ❌ process_image task NOT registered!")
            print(f"   📋 Registered tasks: {[t for t in registered if not t.startswith('celery.')]}")
            return False
            
    except Exception as e:
        print(f"   ❌ Connection error: {e}")
        return False
    
    # 5. Check worker status
    print("\n5. Checking worker status...")
    try:
        inspect = celery_app.control.inspect()
        active = inspect.active()
        
        if active:
            print(f"   ✅ Active workers: {list(active.keys())}")
            
            # Show stats for each worker
            stats = inspect.stats()
            if stats:
                for worker, info in stats.items():
                    print(f"   📊 Worker {worker}:")
                    print(f"      - Pool: {info.get('pool', {}).get('implementation', 'unknown')}")
                    print(f"      - Max concurrency: {info.get('pool', {}).get('max-concurrency', 'unknown')}")
        else:
            print(f"   ⚠️  No active workers found")
            print(f"      Start worker with: celery -A celery_worker worker --loglevel=info --pool=solo")
            
    except Exception as e:
        print(f"   ⚠️  Could not inspect workers: {e}")
    
    print("\n" + "=" * 70)
    print("✅ VERIFICATION COMPLETE")
    print("=" * 70)
    return True

if __name__ == "__main__":
    success = verify_setup()
    
    if success:
        print("\n✅ All checks passed!")
        print("\nNext steps:")
        print("1. Stop your Celery worker (Ctrl+C)")
        print("2. Restart it: celery -A celery_worker worker --loglevel=info --pool=solo")
        print("3. Try uploading an image")
    else:
        print("\n❌ Some checks failed. Fix the issues above.")
        sys.exit(1)