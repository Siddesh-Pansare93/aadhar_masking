#!/usr/bin/env python3
"""
Test script to verify Aadhaar number detection patterns
"""

import sys
import os

# Add src directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.ocr_detector import AadhaarOCRDetector
from src.image_masker import AadhaarImageMasker

def test_pattern_detection():
    """Test our regex patterns with sample text."""
    
    print("🧪 Testing Aadhaar Number Detection Patterns")
    print("=" * 50)
    
    detector = AadhaarOCRDetector()
    masker = AadhaarImageMasker()
    
    # Test cases with different text formats
    test_texts = [
        "Name: John Doe Aadhaar No: 1234 5678 9012 DOB: 01/01/1990",
        "1234567890123456",  # 16 digits (should fail)
        "123456789012",     # 12 continuous digits
        "AADHAAR NUMBER 9876 5432 1098 GOVERNMENT OF INDIA",
        "4 1414 4 4 03/03/2013",  # Your current image text
        "Aadhaar: 4567 8901 2345",
        "Random text without aadhaar number",
        "Multiple numbers: 1234567890 and 9876543210987654 and 1111 2222 3333",
    ]
    
    print("Testing different text patterns:\n")
    
    for i, text in enumerate(test_texts, 1):
        print(f"Test {i}: '{text}'")
        
        result = detector.extract_aadhaar_number(text)
        
        if result:
            masked = masker.mask_aadhaar_number(result)
            print(f"   ✅ Found: {result}")
            print(f"   🎭 Masked: {masked}")
        else:
            print(f"   ❌ No Aadhaar number found")
        
        print()

def main():
    test_pattern_detection()

if __name__ == "__main__":
    main() 