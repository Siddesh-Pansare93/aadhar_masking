#!/usr/bin/env python3
"""
Batch testing script for Aadhaar images
This script will automatically test all images in the sample_data folder
"""

import os
import sys
import glob
from pathlib import Path

# Add src directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.ocr_detector import AadhaarOCRDetector
from src.image_masker import AadhaarImageMasker

def test_all_images():
    """Test all images in the sample_data folder."""
    
    # Supported image extensions
    extensions = ['*.jpg', '*.jpeg', '*.png', '*.bmp', '*.tiff']
    
    # Find all images in sample_data folder
    image_files = []
    for ext in extensions:
        image_files.extend(glob.glob(f"sample_data/{ext}"))
        image_files.extend(glob.glob(f"sample_data/{ext.upper()}"))
    
    if not image_files:
        print("❌ No images found in sample_data folder!")
        print("\n📝 Instructions:")
        print("1. Copy your Aadhaar card images to the 'sample_data' folder")
        print("2. Supported formats: .jpg, .jpeg, .png, .bmp, .tiff")
        print("3. Then run this script again")
        return
    
    print(f"🔍 Found {len(image_files)} image(s) to test:")
    for img in image_files:
        print(f"   📸 {img}")
    
    print("\n" + "="*60)
    
    # Initialize detector and masker
    detector = AadhaarOCRDetector(use_easyocr=True)
    masker = AadhaarImageMasker()
    
    results = []
    
    for i, image_path in enumerate(image_files, 1):
        print(f"\n🔍 Testing Image {i}/{len(image_files)}: {image_path}")
        print("-" * 50)
        
        try:
            # Detect Aadhaar number
            aadhaar_number = detector.detect_with_multiple_methods(image_path)
            
            if aadhaar_number:
                print(f"✅ Aadhaar Number Detected: {aadhaar_number}")
                
                # Mask the number
                masked_number = masker.mask_aadhaar_number(aadhaar_number)
                print(f"🎭 Masked Result: {masked_number}")
                
                # Save result
                output_filename = f"output/masked_{Path(image_path).stem}.jpg"
                os.makedirs("output", exist_ok=True)
                
                success = masker.replace_text_in_image(
                    image_path, aadhaar_number, masked_number, output_filename
                )
                
                if success:
                    print(f"💾 Saved to: {output_filename}")
                
                results.append({
                    'image': image_path,
                    'detected': aadhaar_number,
                    'masked': masked_number,
                    'success': True
                })
                
            else:
                print("❌ No Aadhaar number detected")
                print("💡 Tips:")
                print("   - Ensure image is clear and well-lit")
                print("   - Check that Aadhaar number is fully visible")
                print("   - Try preprocessing the image")
                
                results.append({
                    'image': image_path,
                    'detected': None,
                    'masked': None,
                    'success': False
                })
                
        except Exception as e:
            print(f"❌ Error processing {image_path}: {e}")
            results.append({
                'image': image_path,
                'detected': None,
                'masked': None,
                'success': False,
                'error': str(e)
            })
    
    # Summary
    print("\n" + "="*60)
    print("📊 TESTING SUMMARY")
    print("="*60)
    
    successful = sum(1 for r in results if r['success'])
    total = len(results)
    
    print(f"Total images tested: {total}")
    print(f"Successfully processed: {successful}")
    print(f"Failed: {total - successful}")
    
    if successful > 0:
        print(f"\n✅ Successful Results:")
        for r in results:
            if r['success']:
                print(f"   📸 {r['image']}")
                print(f"      Original: {r['detected']}")
                print(f"      Masked:   {r['masked']}")
    
    if total - successful > 0:
        print(f"\n❌ Failed Images:")
        for r in results:
            if not r['success']:
                print(f"   📸 {r['image']}")
                if 'error' in r:
                    print(f"      Error: {r['error']}")

def main():
    """Main function."""
    print("🚀 Aadhaar Batch Testing Tool")
    print("="*60)
    
    # Check if sample_data directory exists
    if not os.path.exists("sample_data"):
        print("❌ sample_data directory not found!")
        return 1
    
    test_all_images()
    return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code) 