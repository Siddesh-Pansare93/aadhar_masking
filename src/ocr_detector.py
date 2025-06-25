import cv2
import numpy as np
import re
import easyocr
import pytesseract
from PIL import Image
from typing import Optional, List, Tuple
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AadhaarOCRDetector:
    """
    OCR Detector specifically designed for extracting Aadhaar numbers from Aadhaar card images.
    """
    
    def __init__(self, use_easyocr: bool = True):
        """
        Initialize the OCR detector.
        
        Args:
            use_easyocr (bool): Whether to use EasyOCR (True) or Tesseract (False)
        """
        self.use_easyocr = use_easyocr
        
        if use_easyocr:
            # Initialize EasyOCR reader for English
            self.ocr_reader = easyocr.Reader(['en'])
        else:
            # Tesseract will be used directly in method calls
            pass
    
    def preprocess_image(self, image_path: str) -> np.ndarray:
        """
        Preprocess the image to improve OCR accuracy.
        
        Args:
            image_path (str): Path to the input image
            
        Returns:
            np.ndarray: Preprocessed image
        """
        # Load image
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(f"Could not load image from {image_path}")
        
        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Apply Gaussian blur to reduce noise
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        
        # Apply adaptive thresholding
        thresh = cv2.adaptiveThreshold(
            blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
        )
        
        # Apply morphological operations to clean up the image
        kernel = np.ones((1, 1), np.uint8)
        processed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
        processed = cv2.morphologyEx(processed, cv2.MORPH_OPEN, kernel)
        
        return processed
    
    def extract_text_easyocr(self, image: np.ndarray) -> str:
        """
        Extract text using EasyOCR.
        
        Args:
            image (np.ndarray): Preprocessed image
            
        Returns:
            str: Extracted text
        """
        try:
            results = self.ocr_reader.readtext(image)
            
            # Combine all detected text
            extracted_text = ""
            for (bbox, text, conf) in results:
                if conf > 0.5:  # Only consider text with confidence > 50%
                    extracted_text += text + " "
            
            return extracted_text.strip()
        except Exception as e:
            logger.error(f"Error in EasyOCR extraction: {e}")
            return ""
    
    def extract_text_tesseract(self, image: np.ndarray) -> str:
        """
        Extract text using Tesseract OCR.
        
        Args:
            image (np.ndarray): Preprocessed image
            
        Returns:
            str: Extracted text
        """
        try:
            # Convert numpy array to PIL Image
            pil_image = Image.fromarray(image)
            
            # Use Tesseract to extract text
            custom_config = r'--oem 3 --psm 6 -c tessedit_char_whitelist=0123456789 '
            text = pytesseract.image_to_string(pil_image, config=custom_config)
            
            return text.strip()
        except Exception as e:
            logger.error(f"Error in Tesseract extraction: {e}")
            return ""
    
    def extract_aadhaar_number(self, ocr_text: str) -> Optional[str]:
        """
        Extract Aadhaar number from OCR text using regex patterns.
        
        Args:
            ocr_text (str): Raw OCR extracted text
            
        Returns:
            Optional[str]: Aadhaar number if found, None otherwise
        """
        # Clean the text
        cleaned_text = re.sub(r'[^\d\s]', ' ', ocr_text)
        
        # Pattern 1: 12 continuous digits
        pattern1 = r'\b\d{12}\b'
        
        # Pattern 2: 4 digits, space, 4 digits, space, 4 digits
        pattern2 = r'\b\d{4}\s+\d{4}\s+\d{4}\b'
        
        # Pattern 3: More flexible spacing
        pattern3 = r'\b(?:\d{4}[\s]*){3}\b'
        
        patterns = [pattern1, pattern2, pattern3]
        
        for pattern in patterns:
            matches = re.findall(pattern, cleaned_text)
            
            for match in matches:
                # Extract only digits
                digits_only = re.sub(r'\D', '', match)
                
                # Validate that it's exactly 12 digits
                if len(digits_only) == 12:
                    # Format as XXXX XXXX XXXX
                    formatted = f"{digits_only[:4]} {digits_only[4:8]} {digits_only[8:12]}"
                    logger.info(f"Aadhaar number detected: {formatted}")
                    return formatted
        
        logger.warning("No valid Aadhaar number found in OCR text")
        return None
    
    def detect_aadhaar_number(self, image_path: str) -> Optional[str]:
        """
        Main method to detect Aadhaar number from an image.
        
        Args:
            image_path (str): Path to the Aadhaar card image
            
        Returns:
            Optional[str]: Detected Aadhaar number in format 'XXXX XXXX XXXX'
        """
        try:
            # Preprocess the image
            processed_image = self.preprocess_image(image_path)
            
            # Extract text using chosen OCR method
            if self.use_easyocr:
                ocr_text = self.extract_text_easyocr(processed_image)
            else:
                ocr_text = self.extract_text_tesseract(processed_image)
            
            logger.info(f"Extracted OCR text: {ocr_text}")
            
            # Extract Aadhaar number from OCR text
            aadhaar_number = self.extract_aadhaar_number(ocr_text)
            
            return aadhaar_number
            
        except Exception as e:
            logger.error(f"Error in Aadhaar detection: {e}")
            return None
    
    def detect_aadhaar_number_with_location(self, image_path: str) -> Optional[Tuple[str, Tuple[int, int, int, int]]]:
        """
        Detect Aadhaar number and return both the number and its location in the image.
        
        Args:
            image_path (str): Path to the Aadhaar card image
            
        Returns:
            Optional[Tuple[str, Tuple[int, int, int, int]]]: (Aadhaar number, (x, y, width, height)) if found
        """
        try:
            # Preprocess the image
            processed_image = self.preprocess_image(image_path)
            
            if self.use_easyocr:
                # Use EasyOCR and get bounding boxes
                results = self.ocr_reader.readtext(processed_image)
                
                # Look for Aadhaar number in results with bounding box
                for (bbox, text, conf) in results:
                    if conf > 0.5:  # Only consider text with confidence > 50%
                        aadhaar_number = self.extract_aadhaar_number(text)
                        if aadhaar_number:
                            # Convert bbox to standard format (x, y, width, height)
                            x_coords = [point[0] for point in bbox]
                            y_coords = [point[1] for point in bbox]
                            
                            x = int(min(x_coords))
                            y = int(min(y_coords))
                            width = int(max(x_coords) - min(x_coords))
                            height = int(max(y_coords) - min(y_coords))
                            
                            logger.info(f"Aadhaar number detected with location: {aadhaar_number} at ({x}, {y}, {width}, {height})")
                            return (aadhaar_number, (x, y, width, height))
                
                # If no direct match, try extracting from combined text
                all_text = " ".join([text for (bbox, text, conf) in results if conf > 0.5])
                aadhaar_number = self.extract_aadhaar_number(all_text)
                if aadhaar_number:
                    # Try to find multi-part Aadhaar number (e.g., "7227", "5442", "0564")
                    target_parts = aadhaar_number.split()  # ["7227", "5442", "0564"]
                    
                    found_parts = []
                    for part in target_parts:
                        for (bbox, text, conf) in results:
                            if conf > 0.5:
                                text_digits = re.sub(r'\D', '', text)
                                if text_digits == part:
                                    found_parts.append((part, bbox))
                                    break
                    
                    # If we found all 3 parts of the Aadhaar number
                    if len(found_parts) == 3:
                        # Calculate combined bounding box
                        all_x_coords = []
                        all_y_coords = []
                        
                        for part, bbox in found_parts:
                            x_coords = [point[0] for point in bbox]
                            y_coords = [point[1] for point in bbox]
                            all_x_coords.extend(x_coords)
                            all_y_coords.extend(y_coords)
                        
                        # Get overall bounding box
                        x = int(min(all_x_coords))
                        y = int(min(all_y_coords))
                        max_x = int(max(all_x_coords))
                        max_y = int(max(all_y_coords))
                        width = max_x - x
                        height = max_y - y
                        
                        logger.info(f"Multi-part Aadhaar number found: {aadhaar_number} at ({x}, {y}, {width}, {height})")
                        return (aadhaar_number, (x, y, width, height))
                    
                    # Fallback: try to find the best single matching bbox
                    target_digits = aadhaar_number.replace(' ', '')
                    
                    for (bbox, text, conf) in results:
                        if conf > 0.5:
                            text_digits = re.sub(r'\D', '', text)
                            # Check if this text contains significant portion of Aadhaar number
                            if len(text_digits) >= 8:
                                overlap = 0
                                for i in range(len(target_digits) - 7):
                                    if target_digits[i:i+8] in text_digits:
                                        overlap = 8
                                        break
                                
                                if overlap >= 8:
                                    x_coords = [point[0] for point in bbox]
                                    y_coords = [point[1] for point in bbox]
                                    
                                    x = int(min(x_coords))
                                    y = int(min(y_coords))
                                    width = int(max(x_coords) - min(x_coords))
                                    height = int(max(y_coords) - min(y_coords))
                                    
                                    logger.info(f"Aadhaar number found with approximate location: {aadhaar_number} at ({x}, {y}, {width}, {height})")
                                    return (aadhaar_number, (x, y, width, height))
            
            # Fallback to regular detection without location
            aadhaar_number = self.detect_aadhaar_number(image_path)
            if aadhaar_number:
                return (aadhaar_number, None)
            
            return None
            
        except Exception as e:
            logger.error(f"Error in Aadhaar detection with location: {e}")
            return None

    def detect_with_multiple_methods(self, image_path: str) -> Optional[str]:
        """
        Try both EasyOCR and Tesseract for better accuracy.
        
        Args:
            image_path (str): Path to the Aadhaar card image
            
        Returns:
            Optional[str]: Detected Aadhaar number
        """
        # Try EasyOCR first
        self.use_easyocr = True
        self.ocr_reader = easyocr.Reader(['en'])
        result = self.detect_aadhaar_number(image_path)
        
        if result:
            return result
        
        # If EasyOCR fails, try Tesseract
        logger.info("EasyOCR failed, trying Tesseract...")
        self.use_easyocr = False
        result = self.detect_aadhaar_number(image_path)
        
        return result 