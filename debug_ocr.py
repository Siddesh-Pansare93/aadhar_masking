 #!/usr/bin/env python3
"""
Debug script to visualize OCR detection results
"""

import cv2
import numpy as np
import easyocr
import sys
import os

def debug_ocr_detection(image_path):
    """Debug OCR detection and visualize results."""
    
    print(f"🔍 Debugging OCR detection for: {image_path}")
    
    # Initialize EasyOCR
    reader = easyocr.Reader(['en'])
    
    # Load image
    image = cv2.imread(image_path)
    if image is None:
        print(f"❌ Could not load image: {image_path}")
        return
    
    original = image.copy()
    
    # Get OCR results
    results = reader.readtext(image)
    
    print(f"\n📊 Found {len(results)} text elements:")
    print("=" * 80)
    
    # Process each detected text
    for i, (bbox, text, conf) in enumerate(results):
        print(f"\n{i+1}. Text: '{text}'")
        print(f"   Confidence: {conf:.3f}")
        print(f"   Bbox: {bbox}")
        
        # Check if this might contain Aadhaar number
        digits = ''.join(filter(str.isdigit, text))
        print(f"   Digits only: '{digits}' (length: {len(digits)})")
        
        # Convert bbox to rectangle coordinates
        x_coords = [point[0] for point in bbox]
        y_coords = [point[1] for point in bbox]
        
        x = int(min(x_coords))
        y = int(min(y_coords))
        width = int(max(x_coords) - min(x_coords))
        height = int(max(y_coords) - min(y_coords))
        
        print(f"   Rectangle: ({x}, {y}) size {width}x{height}")
        
        # Draw bounding box on image
        color = (0, 255, 0) if conf > 0.5 else (0, 0, 255)  # Green for high conf, red for low
        thickness = 2 if len(digits) >= 8 else 1  # Thick for potential Aadhaar numbers
        
        # Draw rectangle
        cv2.rectangle(image, (x, y), (x + width, y + height), color, thickness)
        
        # Add text label
        label = f"{i+1}: {conf:.2f}"
        cv2.putText(image, label, (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
        
        # Highlight potential Aadhaar numbers
        if len(digits) >= 12:
            print(f"   🎯 POTENTIAL AADHAAR NUMBER!")
            cv2.putText(image, "AADHAAR?", (x, y+height+20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 255), 2)
    
    # Save debug image
    debug_output = f"output/debug_{os.path.basename(image_path)}"
    cv2.imwrite(debug_output, image)
    
    print(f"\n💾 Debug visualization saved to: {debug_output}")
    print(f"🔍 Original image dimensions: {original.shape[1]}x{original.shape[0]}")
    
    return results

def main():
    if len(sys.argv) != 2:
        print("Usage: python debug_ocr.py <image_path>")
        print("Example: python debug_ocr.py sample_data/hasan.jpg")
        sys.exit(1)
    
    image_path = sys.argv[1]
    
    if not os.path.exists(image_path):
        print(f"❌ Image not found: {image_path}")
        sys.exit(1)
    
    # Ensure output directory exists
    os.makedirs("output", exist_ok=True)
    
    # Run debug
    results = debug_ocr_detection(image_path)
    
    print(f"\n🎯 Summary:")
    print(f"   Total text elements: {len(results)}")
    high_conf = sum(1 for _, _, conf in results if conf > 0.5)
    print(f"   High confidence (>0.5): {high_conf}")
    
    potential_aadhaar = []
    for bbox, text, conf in results:
        digits = ''.join(filter(str.isdigit, text))
        if len(digits) >= 12:
            potential_aadhaar.append((text, digits, conf))
    
    if potential_aadhaar:
        print(f"   Potential Aadhaar numbers found: {len(potential_aadhaar)}")
        for text, digits, conf in potential_aadhaar:
            print(f"     - '{text}' -> '{digits}' (conf: {conf:.3f})")
    else:
        print(f"   No complete Aadhaar numbers detected")

if __name__ == "__main__":
    main() 