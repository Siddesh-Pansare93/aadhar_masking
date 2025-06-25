#!/usr/bin/env python3
"""
Test setup script to verify that all dependencies are installed correctly
and basic functionality works.
"""

import sys
import os

def test_imports():
    """Test that all required packages can be imported."""
    print("🧪 Testing package imports...")
    
    try:
        import cv2
        print("✅ OpenCV imported successfully")
    except ImportError as e:
        print(f"❌ OpenCV import failed: {e}")
        return False
    
    try:
        import numpy as np
        print("✅ NumPy imported successfully")
    except ImportError as e:
        print(f"❌ NumPy import failed: {e}")
        return False
    
    try:
        import PIL
        print("✅ Pillow imported successfully")
    except ImportError as e:
        print(f"❌ Pillow import failed: {e}")
        return False
    
    try:
        import easyocr
        print("✅ EasyOCR imported successfully")
    except ImportError as e:
        print(f"❌ EasyOCR import failed: {e}")
        return False
    
    try:
        import pytesseract
        print("✅ PyTesseract imported successfully")
    except ImportError as e:
        print(f"❌ PyTesseract import failed: {e}")
        print("💡 Note: Tesseract OCR binary may not be installed")
    
    return True

def test_project_modules():
    """Test that project modules can be imported."""
    print("\n🔧 Testing project modules...")
    
    # Add src to path
    sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
    
    try:
        from src.ocr_detector import AadhaarOCRDetector
        print("✅ OCR Detector module imported successfully")
    except ImportError as e:
        print(f"❌ OCR Detector import failed: {e}")
        return False
    
    try:
        from src.image_masker import AadhaarImageMasker
        print("✅ Image Masker module imported successfully")
    except ImportError as e:
        print(f"❌ Image Masker import failed: {e}")
        return False
    
    return True

def test_masking_functionality():
    """Test the basic masking functionality."""
    print("\n🎭 Testing masking functionality...")
    
    sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
    
    try:
        from src.image_masker import AadhaarImageMasker
        
        masker = AadhaarImageMasker()
        
        # Test cases
        test_cases = [
            "1234 5678 9012",
            "123456789012",
            "9876 5432 1098"
        ]
        
        for test_number in test_cases:
            try:
                masked = masker.mask_aadhaar_number(test_number)
                expected_format = test_number.replace(test_number[:4], "XXXX")
                if " " in test_number:
                    expected = f"XXXX {test_number[5:]}"
                else:
                    digits = test_number.replace(" ", "")
                    expected = f"XXXX {digits[4:8]} {digits[8:12]}"
                
                print(f"   Original: {test_number}")
                print(f"   Masked:   {masked}")
                print(f"   Expected: {expected}")
                
                if masked.startswith("XXXX"):
                    print("   ✅ Masking successful")
                else:
                    print("   ❌ Masking failed")
                print()
                
            except Exception as e:
                print(f"   ❌ Error masking {test_number}: {e}")
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ Masking functionality test failed: {e}")
        return False

def test_ocr_initialization():
    """Test OCR detector initialization."""
    print("🔍 Testing OCR detector initialization...")
    
    sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
    
    try:
        from src.ocr_detector import AadhaarOCRDetector
        
        # Test EasyOCR initialization
        print("   Testing EasyOCR initialization...")
        detector_easy = AadhaarOCRDetector(use_easyocr=True)
        print("   ✅ EasyOCR detector initialized")
        
        # Test Tesseract initialization
        print("   Testing Tesseract initialization...")
        detector_tesseract = AadhaarOCRDetector(use_easyocr=False)
        print("   ✅ Tesseract detector initialized")
        
        return True
        
    except Exception as e:
        print(f"   ❌ OCR initialization failed: {e}")
        return False

def create_sample_directories():
    """Create necessary directories for the project."""
    print("📁 Creating project directories...")
    
    directories = ["sample_data", "output"]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"   ✅ Created/verified directory: {directory}")

def main():
    """Run all tests."""
    print("🚀 Aadhaar Masking Project - Setup Test")
    print("=" * 50)
    
    # Create directories
    create_sample_directories()
    
    # Run tests
    tests = [
        ("Package Imports", test_imports),
        ("Project Modules", test_project_modules),
        ("Masking Functionality", test_masking_functionality),
        ("OCR Initialization", test_ocr_initialization)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "="*50)
    print("📊 TEST SUMMARY")
    print("="*50)
    
    all_passed = True
    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name:25} {status}")
        if not passed:
            all_passed = False
    
    print("="*50)
    
    if all_passed:
        print("🎉 All tests passed! Your setup is ready.")
        print("\n📝 Next steps:")
        print("1. Place Aadhaar card images in the 'sample_data' folder")
        print("2. Run: python main.py --image sample_data/your_image.jpg")
        print("3. Check the 'output' folder for results")
    else:
        print("⚠️  Some tests failed. Please check the error messages above.")
        print("\n🔧 Troubleshooting:")
        print("1. Make sure all dependencies are installed: pip install -r requirements.txt")
        print("2. Check Python version (3.7+ recommended)")
        print("3. For Tesseract issues, install Tesseract OCR separately")
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code) 