#!/usr/bin/env python3
"""
MHC Image-to-Image API Connection Test Script

This script tests the connection to the MHC API for image-to-image processing.
"""

import sys
import os
import json
import time

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_mhc_connection():
    """Test MHC API connection."""
    
    print("=" * 60)
    print("MHC Image-to-Image API Connection Test")
    print("=" * 60)
    
    # 1. Check environment variables
    print("\n[1] Checking environment variables...")
    
    mhc_app = os.getenv("MHC_APP", "")
    mhc_biz = os.getenv("MHC_BIZ", "")
    mhc_region = os.getenv("MHC_REGION", "")
    mhc_env = os.getenv("MHC_ENV", "outer")
    mhc_api_path = os.getenv("MHC_API_PATH", "")
    
    print(f"  MHC_APP: {mhc_app}")
    print(f"  MHC_BIZ: {mhc_biz}")
    print(f"  MHC_REGION: {mhc_region}")
    print(f"  MHC_ENV: {mhc_env}")
    print(f"  MHC_API_PATH: {mhc_api_path[:50]}..." if len(mhc_api_path) > 50 else f"  MHC_API_PATH: {mhc_api_path}")
    
    if not all([mhc_app, mhc_biz, mhc_region, mhc_api_path]):
        print("\n  ❌ Error: Missing required environment variables!")
        return False
    
    print("  ✅ Environment variables loaded")
    
    # 2. Try to import SDK
    print("\n[2] Checking MHC SDK...")
    
    try:
        from lib.ai import api as mhc_api
        print("  ✅ SDK module imported")
    except ImportError as e:
        print(f"  ❌ Error importing SDK: {e}")
        print("  Please ensure the MHC SDK is installed in lib/ai/api.py")
        return False
    
    # 3. Try to initialize client
    print("\n[3] Initializing MHC client...")
    
    try:
        cli = mhc_api.AiApi(mhc_app, mhc_biz, mhc_region, env=mhc_env)
        print("  ✅ Client initialized successfully")
    except NotImplementedError as e:
        print(f"  ❌ SDK is placeholder: {e}")
        print("\n  ⚠️  You need to replace lib/ai/api.py with the actual MHC SDK")
        print("     The placeholder file shows the required interface.")
        return False
    except Exception as e:
        print(f"  ❌ Error initializing client: {e}")
        return False
    
    # 4. Test API call with a sample image
    print("\n[4] Testing API call...")
    
    # Use a public test image
    test_image_url = "https://xiuxiu-pro.meitudata.com/matting/fa5d4d604ed502219c24d8cbf2bbc5ce.png"
    
    params = {
        "parameter": {
            "prompt": "realistic photo, natural lighting",
            "negative_prompt": "artificial, fake, plastic",
            "denoising_strength": 0.2,
            "rsp_media_type": "url"
        }
    }
    
    print(f"  Test image: {test_image_url}")
    print(f"  API path: {mhc_api_path}")
    
    try:
        print("\n  Submitting async task...")
        task_result = cli.runAsync(
            [{"url": test_image_url}],
            params,
            mhc_api_path,
            "mtlab"
        )
        
        print(f"  Response: {json.dumps(task_result, indent=2, ensure_ascii=False)[:500]}")
        
        if "data" in task_result and "result" in task_result.get("data", {}):
            task_id = task_result["data"]["result"]["id"]
            print(f"\n  ✅ Task submitted! Task ID: {task_id}")
            
            # Poll for result
            print("\n[5] Polling for result...")
            max_attempts = 10
            for attempt in range(max_attempts):
                print(f"  Attempt {attempt + 1}/{max_attempts}...")
                time.sleep(3)
                
                result = cli.queryResult(task_id)
                status = result.get("data", {}).get("status", "unknown")
                
                print(f"  Status: {status}")
                
                if status in ["success", "completed"]:
                    print(f"\n  ✅ Task completed!")
                    print(f"  Result: {json.dumps(result, indent=2, ensure_ascii=False)[:1000]}")
                    return True
                elif status in ["failed", "error"]:
                    print(f"\n  ❌ Task failed: {result}")
                    return False
            
            print(f"\n  ⚠️  Task still processing after {max_attempts} attempts")
            return True  # Connection works, just timeout
            
        else:
            print(f"\n  ❌ Unexpected response format")
            return False
            
    except Exception as e:
        print(f"\n  ❌ API call failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_image_model_client():
    """Test the ImageModelClient from the app."""
    
    print("\n" + "=" * 60)
    print("Testing ImageModelClient Integration")
    print("=" * 60)
    
    try:
        from app.services.image_model import ImageModelClient, MHC_SDK_AVAILABLE
        
        print(f"\n[1] MHC SDK Available: {MHC_SDK_AVAILABLE}")
        
        client = ImageModelClient()
        print(f"[2] MHC Client Initialized: {client.mhc_client is not None}")
        
        if client.mhc_client:
            print("  ✅ ImageModelClient ready with MHC support")
            return True
        else:
            print("  ⚠️  ImageModelClient running without MHC (will fallback)")
            return False
            
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("MHC API Connection Test Suite")
    print("=" * 60)
    
    # Test 1: Direct MHC connection
    mhc_ok = test_mhc_connection()
    
    # Test 2: App integration
    app_ok = test_image_model_client()
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    print(f"  MHC Direct Connection: {'✅ OK' if mhc_ok else '❌ FAILED'}")
    print(f"  App Integration:       {'✅ OK' if app_ok else '❌ FAILED'}")
    print("=" * 60)
    
    if not mhc_ok:
        print("\n⚠️  To fix MHC connection:")
        print("   1. Replace lib/ai/api.py with the actual MHC SDK")
        print("   2. Or install the SDK package and update the import")
        print("   3. Verify .env has correct MHC_APP, MHC_BIZ, MHC_REGION, MHC_API_PATH")
