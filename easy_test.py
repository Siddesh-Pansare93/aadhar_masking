#!/usr/bin/env python3
"""
Easy test script for Aadhaar masking
"""

import os
import sys

def main():
    print("🎉 Aadhaar Masking System - Easy Test")
    print("=" * 50)
    
    # Check if user provided image
    if len(sys.argv) > 1:
        image_path = sys.argv[1]
        if not os.path.exists(image_path):
            print(f"❌ Image not found: {image_path}")
            return 1
            
        output_name = f"output/masked_{os.path.basename(image_path)}"
        
        print(f"📸 Processing: {image_path}")
        print(f"💾 Output will be: {output_name}")
        
        # Run the main script
        os.system(f'python main.py --image "{image_path}" --output "{output_name}"')
        
        print(f"\n✅ Done! Check the result in: {output_name}")
        
    else:
        print("📝 Usage Examples:")
        print("  python easy_test.py sample_data/hasan.jpg")
        print("  python easy_test.py sample_data/your_aadhaar.jpg")
        print("\n📋 Available commands:")
        print("  python main.py --image sample_data/hasan.jpg --output output/result.jpg")
        print("  python test_images.py  # Test all images in sample_data")
        print("  python debug_ocr.py sample_data/hasan.jpg  # Debug OCR detection")
        
        print(f"\n📁 Current files in sample_data:")
        if os.path.exists("sample_data"):
            files = [f for f in os.listdir("sample_data") if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
            if files:
                for f in files:
                    print(f"  📸 {f}")
            else:
                print("  (No image files found)")
        
        print(f"\n📁 Generated results in output:")
        if os.path.exists("output"):
            files = [f for f in os.listdir("output") if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
            if files:
                for f in files:
                    print(f"  🎭 {f}")
            else:
                print("  (No output files yet)")

if __name__ == "__main__":
    main() 