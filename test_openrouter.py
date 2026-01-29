#!/usr/bin/env python3
"""
Integration test for the SizeEstimator with OpenRouter.
"""
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Check for API key
api_key = os.getenv('OPENROUTER_API_KEY')
if not api_key or api_key == 'your_openrouter_api_key_here':
    print("❌ OPENROUTER_API_KEY not set in .env file")
    sys.exit(1)

print("✓ OPENROUTER_API_KEY is set")

# Try to import and initialize SizeEstimator
try:
    from size_estimator import SizeEstimator
    print("✓ SizeEstimator imported successfully")
    
    estimator = SizeEstimator()
    print("✓ SizeEstimator initialized successfully")
    
    # Find a test image
    test_image_path = None
    search_paths = [
        '/mnt/b/local_projects/virtual-try-on/web/static/uploads/users',
        '/mnt/b/local_projects/virtual-try-on/web/static/uploads',
        '/mnt/b/local_projects/virtual-try-on/web/static'
    ]
    
    for path in search_paths:
        if os.path.exists(path):
            for file in os.listdir(path):
                if file.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')):
                    test_image_path = os.path.join(path, file)
                    break
        if test_image_path:
            break
    
    if not test_image_path:
        print("\n⚠️  No test image found. Skipping size estimation test.")
        print("   Upload a user photo to test the full integration.")
        sys.exit(0)
    
    print(f"✓ Found test image: {test_image_path}")
    
    # Test size estimation
    print("\nTesting size estimation...")
    measurements, size_category = estimator.estimate_size(test_image_path, height_cm=175)
    
    print(f"\n✅ Size estimation successful!")
    print(f"   Measurements: {measurements}")
    print(f"   Recommended size: {size_category}")
    print("\n✅ All checks passed! OpenRouter integration is working correctly.")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
