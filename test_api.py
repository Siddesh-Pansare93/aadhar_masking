#!/usr/bin/env python3
"""
Test script for the Aadhaar UID Masking API.
Tests both single and bulk image processing endpoints.
"""

import requests
import os
import time
from pathlib import Path

# Configuration
API_BASE_URL = "http://localhost:8000"
TEST_IMAGES_DIR = Path("sample_data")

def test_health_check():
    """Test the health check endpoint."""
    print("🏥 Testing health check...")
    try:
        response = requests.get(f"{API_BASE_URL}/health")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Health check passed: {data['status']}")
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False

def test_single_image_processing(image_path):
    """Test single image processing endpoint."""
    print(f"📄 Testing single image processing with: {image_path}")
    
    if not os.path.exists(image_path):
        print(f"❌ Test image not found: {image_path}")
        return False
    
    try:
        with open(image_path, 'rb') as f:
            files = {'file': f}
            start_time = time.time()
            response = requests.post(f"{API_BASE_URL}/process-image", files=files)
            end_time = time.time()
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Single image processing successful!")
            print(f"   Filename: {data['filename']}")
            print(f"   UID Numbers: {data['uid_numbers']}")
            print(f"   Masked Image URL: {data['masked_image_url']}")
            print(f"   Processing Time: {data['processing_time']:.2f}s")
            print(f"   Locations Found: {data['locations_found']}")
            print(f"   Total Request Time: {end_time - start_time:.2f}s")
            return True
        elif response.status_code == 422:
            print(f"⚠️  No Aadhaar number detected in image")
            return False
        else:
            error_data = response.json() if response.headers.get('content-type') == 'application/json' else {}
            print(f"❌ Single image processing failed: {response.status_code}")
            print(f"   Error: {error_data.get('detail', 'Unknown error')}")
            return False
    except Exception as e:
        print(f"❌ Single image processing error: {e}")
        return False

def test_bulk_image_processing(image_paths):
    """Test bulk image processing endpoint."""
    print(f"📚 Testing bulk image processing with {len(image_paths)} images...")
    
    # Filter existing images
    existing_images = [path for path in image_paths if os.path.exists(path)]
    if not existing_images:
        print("❌ No test images found for bulk processing")
        return False
    
    if len(existing_images) != len(image_paths):
        print(f"⚠️  Only {len(existing_images)} out of {len(image_paths)} images found")
    
    try:
        files = []
        for image_path in existing_images:
            files.append(('files', open(image_path, 'rb')))
        
        start_time = time.time()
        response = requests.post(f"{API_BASE_URL}/process-bulk", files=files)
        end_time = time.time()
        
        # Close file handles
        for _, file_handle in files:
            file_handle.close()
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Bulk processing completed!")
            print(f"   Total Images: {data['total_images']}")
            print(f"   Successful: {data['successful_processes']}")
            print(f"   Failed: {data['failed_processes']}")
            print(f"   Total Request Time: {end_time - start_time:.2f}s")
            
            if data['results']:
                print(f"   Results:")
                for i, result in enumerate(data['results'], 1):
                    print(f"     {i}. {result['filename']} - {result['uid_numbers']} - {result['processing_time']:.2f}s")
            
            if data['errors']:
                print(f"   Errors:")
                for error in data['errors']:
                    print(f"     - {error}")
            
            return True
        else:
            error_data = response.json() if response.headers.get('content-type') == 'application/json' else {}
            print(f"❌ Bulk processing failed: {response.status_code}")
            print(f"   Error: {error_data.get('detail', 'Unknown error')}")
            return False
    except Exception as e:
        print(f"❌ Bulk processing error: {e}")
        return False

def test_invalid_file():
    """Test with invalid file type."""
    print("🚫 Testing with invalid file type...")
    
    # Create a temporary text file
    test_file_path = "test_invalid.txt"
    with open(test_file_path, 'w') as f:
        f.write("This is not an image file")
    
    try:
        with open(test_file_path, 'rb') as f:
            files = {'file': f}
            response = requests.post(f"{API_BASE_URL}/process-image", files=files)
        
        if response.status_code == 400:
            print("✅ Invalid file type correctly rejected")
            return True
        else:
            print(f"❌ Expected 400 status code, got {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Invalid file test error: {e}")
        return False
    finally:
        # Clean up
        if os.path.exists(test_file_path):
            os.remove(test_file_path)

def test_cleanup():
    """Test the cleanup endpoint."""
    print("🧹 Testing cleanup endpoint...")
    try:
        response = requests.delete(f"{API_BASE_URL}/cleanup")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Cleanup successful: {data['message']}")
            return True
        else:
            print(f"❌ Cleanup failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Cleanup error: {e}")
        return False

def main():
    """Run all tests."""
    print("🚀 Starting Aadhaar UID Masking API Tests")
    print("=" * 50)
    
    # Test results
    results = []
    
    # Health check
    results.append(("Health Check", test_health_check()))
    
    # Find test images
    test_images = []
    if TEST_IMAGES_DIR.exists():
        for ext in ['*.jpg', '*.jpeg', '*.png']:
            test_images.extend(TEST_IMAGES_DIR.glob(ext))
    
    # If no test images in sample_data, check current directory
    if not test_images:
        current_dir = Path(".")
        for ext in ['*.jpg', '*.jpeg', '*.png']:
            test_images.extend(current_dir.glob(ext))
    
    if test_images:
        # Single image test
        results.append(("Single Image Processing", test_single_image_processing(str(test_images[0]))))
        
        # Bulk processing test (use up to 3 images)
        if len(test_images) > 1:
            bulk_images = [str(img) for img in test_images[:3]]
            results.append(("Bulk Image Processing", test_bulk_image_processing(bulk_images)))
    else:
        print("⚠️  No test images found. Skipping image processing tests.")
        print("   To test image processing, place some Aadhaar card images in the 'sample_data' directory")
    
    # Invalid file test
    results.append(("Invalid File Type", test_invalid_file()))
    
    # Cleanup test
    results.append(("Cleanup", test_cleanup()))
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Results Summary:")
    
    passed = 0
    total = 0
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {test_name}: {status}")
        if result:
            passed += 1
        total += 1
    
    print(f"\n🎯 Overall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! API is working correctly.")
        return 0
    else:
        print("⚠️  Some tests failed. Check the API server and configuration.")
        return 1

if __name__ == "__main__":
    exit(main()) 