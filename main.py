#!/usr/bin/env python3
"""
Aadhaar Masking Project - Main Application

This application demonstrates OCR detection of Aadhaar numbers from card images
and masking functionality.
"""

import os
import sys
import argparse
from pathlib import Path

# Add src directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.ocr_detector import AadhaarOCRDetector
from src.image_masker import AadhaarImageMasker

def main():
    """Main application function."""
    parser = argparse.ArgumentParser(description='Aadhaar Card OCR and Masking Tool')
    parser.add_argument('--image', '-i', type=str, required=True, 
                       help='Path to the Aadhaar card image')
    parser.add_argument('--output', '-o', type=str, 
                       help='Output path for masked image (optional)')
    parser.add_argument('--ocr-method', choices=['easyocr', 'tesseract', 'both'], 
                       default='both', help='OCR method to use')
    
    args = parser.parse_args()
    
    # Check if input image exists
    if not os.path.exists(args.image):
        print(f"Error: Image file '{args.image}' not found!")
        return 1
    
    print("🔍 Aadhaar Card OCR Detection Started...")
    print(f"📸 Processing image: {args.image}")
    
    # Initialize OCR detector
    detector = AadhaarOCRDetector(use_easyocr=True)
    
    # Detect Aadhaar number with location
    detector.use_easyocr = (args.ocr_method != 'tesseract')  # Use EasyOCR unless specifically tesseract
    
    detection_result = detector.detect_aadhaar_number_with_location(args.image)
    
    if detection_result:
        aadhaar_number, bbox = detection_result
        print(f"✅ Aadhaar Number Detected: {aadhaar_number}")
        
        if bbox:
            x, y, width, height = bbox
            print(f"📍 Location found: ({x}, {y}) with size {width}x{height}")
        
        # Initialize masker
        masker = AadhaarImageMasker()
        
        # Mask the Aadhaar number
        masked_number = masker.mask_aadhaar_number(aadhaar_number)
        print(f"🎭 Masked Aadhaar Number: {masked_number}")
        
        # Save masked image if output path provided
        if args.output:
            if bbox:
                # Use the detected location for precise replacement
                success = masker.replace_text_at_location(
                    args.image, aadhaar_number, masked_number, bbox, args.output
                )
            else:
                # Fallback to general replacement
                success = masker.replace_text_in_image(
                    args.image, aadhaar_number, masked_number, args.output
                )
            
            if success:
                print(f"💾 Masked image saved: {args.output}")
            else:
                print("❌ Failed to save masked image")
        
        return 0
    else:
        print("❌ No Aadhaar number detected in the image!")
        print("\n🔧 Troubleshooting tips:")
        print("1. Ensure the image is clear and well-lit")
        print("2. Make sure the Aadhaar number is visible and not cropped")
        print("3. Try a different OCR method using --ocr-method flag")
        return 1

def demo_with_sample():
    """Demo function for testing without command line arguments."""
    print("🚀 Aadhaar OCR Detection Demo")
    print("=" * 40)
    
    # Create sample data directory
    os.makedirs("sample_data", exist_ok=True)
    
    # Test with a sample Aadhaar number pattern
    sample_text = "1234 5678 9012"
    
    # Initialize masker to test masking functionality
    masker = AadhaarImageMasker()
    masked = masker.mask_aadhaar_number(sample_text)
    
    print(f"Original: {sample_text}")
    print(f"Masked:   {masked}")
    print("\n📝 Place your Aadhaar card images in the 'sample_data' folder")
    print("📝 Then run: python main.py --image sample_data/your_aadhaar.jpg")

if __name__ == "__main__":
    if len(sys.argv) == 1:
        # Run demo if no arguments provided
        demo_with_sample()
    else:
        # Run main application
        exit_code = main()
        sys.exit(exit_code) 