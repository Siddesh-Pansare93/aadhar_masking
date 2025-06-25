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
    
    def detect_aadhaar_number_with_all_locations(self, image_path: str) -> Optional[Tuple[str, List[Tuple[int, int, int, int]]]]:
        """
        Detect Aadhaar number and return both the number and ALL its locations in the image.
        
        Args:
            image_path (str): Path to the Aadhaar card image
            
        Returns:
            Optional[Tuple[str, List[Tuple[int, int, int, int]]]]: (Aadhaar number, list of (x, y, width, height)) if found
        """
        try:
            # Preprocess the image
            processed_image = self.preprocess_image(image_path)
            
            if self.use_easyocr:
                # Use EasyOCR and get bounding boxes
                results = self.ocr_reader.readtext(processed_image)
                
                # First, extract the Aadhaar number from combined text
                all_text = " ".join([text for (bbox, text, conf) in results if conf > 0.5])
                aadhaar_number = self.extract_aadhaar_number(all_text)
                
                if aadhaar_number:
                    all_locations = []
                    target_parts = aadhaar_number.split()  # ["7227", "5442", "0564"]
                    target_digits = aadhaar_number.replace(' ', '')  # "722754420564"
                    
                    logger.info(f"Searching for ALL occurrences of: {aadhaar_number}")
                    
                    # Method 1: Look for complete multi-part Aadhaar numbers
                    potential_groups = []
                    
                    # Group nearby text elements that might form complete Aadhaar numbers
                    for i, (bbox1, text1, conf1) in enumerate(results):
                        if conf1 > 0.5:
                            text1_digits = re.sub(r'\D', '', text1)
                            if len(text1_digits) == 4 and text1_digits in target_digits:
                                # This might be the start of an Aadhaar number
                                group = [(text1, bbox1)]
                                
                                # Look for the next 2 parts nearby
                                for j, (bbox2, text2, conf2) in enumerate(results):
                                    if i != j and conf2 > 0.5:
                                        text2_digits = re.sub(r'\D', '', text2)
                                        if len(text2_digits) == 4 and text2_digits in target_digits:
                                            # Check if it's nearby (same general area)
                                            x1_coords = [p[0] for p in bbox1]
                                            y1_coords = [p[1] for p in bbox1]
                                            x2_coords = [p[0] for p in bbox2]
                                            y2_coords = [p[1] for p in bbox2]
                                            
                                            # If elements are close to each other (same line roughly)
                                            y1_center = (min(y1_coords) + max(y1_coords)) / 2
                                            y2_center = (min(y2_coords) + max(y2_coords)) / 2
                                            
                                            if abs(y1_center - y2_center) < 50:  # Same line tolerance
                                                group.append((text2, bbox2))
                                
                                # If we found 3 parts that form the complete Aadhaar number
                                if len(group) == 3:
                                    group_digits = ''.join([re.sub(r'\D', '', text) for text, bbox in group])
                                    if group_digits == target_digits:
                                        # Calculate combined bounding box for this group
                                        all_x_coords = []
                                        all_y_coords = []
                                        
                                        for text, bbox in group:
                                            x_coords = [point[0] for point in bbox]
                                            y_coords = [point[1] for point in bbox]
                                            all_x_coords.extend(x_coords)
                                            all_y_coords.extend(y_coords)
                                        
                                        x = int(min(all_x_coords))
                                        y = int(min(all_y_coords))
                                        max_x = int(max(all_x_coords))
                                        max_y = int(max(all_y_coords))
                                        width = max_x - x
                                        height = max_y - y
                                        
                                        all_locations.append((x, y, width, height))
                                        logger.info(f"Found complete Aadhaar group at: ({x}, {y}, {width}, {height})")
                    
                    # Method 2: Look for single text blocks containing the full number
                    for (bbox, text, conf) in results:
                        if conf > 0.5:
                            # Check if this single text block contains the full Aadhaar number
                            text_digits = re.sub(r'\D', '', text)
                            if target_digits in text_digits and len(text_digits) >= 12:
                                x_coords = [point[0] for point in bbox]
                                y_coords = [point[1] for point in bbox]
                                
                                x = int(min(x_coords))
                                y = int(min(y_coords))
                                width = int(max(x_coords) - min(x_coords))
                                height = int(max(y_coords) - min(y_coords))
                                
                                # Check if this location is already covered by a group
                                is_duplicate = False
                                for existing_x, existing_y, existing_w, existing_h in all_locations:
                                    if (abs(x - existing_x) < 50 and abs(y - existing_y) < 50):
                                        is_duplicate = True
                                        break
                                
                                if not is_duplicate:
                                    all_locations.append((x, y, width, height))
                                    logger.info(f"Found single block Aadhaar at: ({x}, {y}, {width}, {height})")
                    
                    if all_locations:
                        logger.info(f"Total locations found: {len(all_locations)}")
                        return (aadhaar_number, all_locations)
            
            # Fallback to regular detection without location
            aadhaar_number = self.detect_aadhaar_number(image_path)
            if aadhaar_number:
                return (aadhaar_number, [])
            
            return None
            
        except Exception as e:
            logger.error(f"Error in Aadhaar detection with all locations: {e}")
            return None

    def detect_aadhaar_number_with_location(self, image_path: str) -> Optional[Tuple[str, Tuple[int, int, int, int]]]:
        """
        Detect Aadhaar number and return both the number and its location in the image.
        (Legacy method - returns only first location)
        
        Args:
            image_path (str): Path to the Aadhaar card image
            
        Returns:
            Optional[Tuple[str, Tuple[int, int, int, int]]]: (Aadhaar number, (x, y, width, height)) if found
        """
        result = self.detect_aadhaar_number_with_all_locations(image_path)
        if result:
            aadhaar_number, locations = result
            if locations:
                return (aadhaar_number, locations[0])  # Return first location
            return (aadhaar_number, None)
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