import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from typing import Optional, Tuple, List
import logging
import easyocr
import re

logger = logging.getLogger(__name__)

class AadhaarImageMasker:
    """
    Class for masking the first 4 digits of Aadhaar numbers in images.
    """
    
    def __init__(self):
        """Initialize the image masker."""
        self.ocr_reader = easyocr.Reader(['en'])
    
    def mask_aadhaar_number(self, aadhaar_number: str) -> str:
        """
        Mask the first 4 digits of an Aadhaar number with 'X'.
        
        Args:
            aadhaar_number (str): Original Aadhaar number (e.g., "1234 5678 9012")
            
        Returns:
            str: Masked Aadhaar number (e.g., "XXXX 5678 9012")
        """
        if not aadhaar_number or len(aadhaar_number.replace(' ', '')) != 12:
            raise ValueError("Invalid Aadhaar number format")
        
        # Remove spaces and mask first 4 digits
        digits_only = aadhaar_number.replace(' ', '')
        masked = 'XXXX' + digits_only[4:]
        
        # Format back with spaces
        formatted_masked = f"{masked[:4]} {masked[4:8]} {masked[8:12]}"
        
        return formatted_masked
    
    def find_text_location_in_image(self, image_path: str, target_text: str) -> Optional[Tuple[int, int, int, int]]:
        """
        Find the location of text in the image using EasyOCR.
        
        Args:
            image_path (str): Path to the image
            target_text (str): Text to find in the image
            
        Returns:
            Optional[Tuple[int, int, int, int]]: Bounding box (x, y, width, height) if found
        """
        try:
            # Load image
            image = cv2.imread(image_path)
            if image is None:
                logger.error(f"Could not load image: {image_path}")
                return None
            
            # Use EasyOCR to detect text and get bounding boxes
            results = self.ocr_reader.readtext(image)
            
            # Clean target text for comparison
            target_digits = re.sub(r'\D', '', target_text)  # Remove non-digits
            
            # Search for the target text in OCR results
            for (bbox, text, conf) in results:
                if conf < 0.5:  # Skip low confidence detections
                    continue
                
                # Clean detected text
                detected_digits = re.sub(r'\D', '', text)
                
                # Check if this text contains our target Aadhaar number
                if len(detected_digits) >= 12 and target_digits in detected_digits:
                    # Convert bbox to standard format (x, y, width, height)
                    x_coords = [point[0] for point in bbox]
                    y_coords = [point[1] for point in bbox]
                    
                    x = int(min(x_coords))
                    y = int(min(y_coords))
                    width = int(max(x_coords) - min(x_coords))
                    height = int(max(y_coords) - min(y_coords))
                    
                    logger.info(f"Found text '{text}' at location: ({x}, {y}, {width}, {height})")
                    return (x, y, width, height)
            
            # If exact match not found, try partial matching
            for (bbox, text, conf) in results:
                if conf < 0.5:
                    continue
                
                detected_digits = re.sub(r'\D', '', text)
                
                # Check if any part of the Aadhaar number is in this text
                if len(detected_digits) >= 8:  # At least 8 digits
                    # Check if significant portion matches
                    for i in range(len(target_digits) - 7):
                        if target_digits[i:i+8] in detected_digits:
                            x_coords = [point[0] for point in bbox]
                            y_coords = [point[1] for point in bbox]
                            
                            x = int(min(x_coords))
                            y = int(min(y_coords))
                            width = int(max(x_coords) - min(x_coords))
                            height = int(max(y_coords) - min(y_coords))
                            
                            logger.info(f"Found partial match '{text}' at location: ({x}, {y}, {width}, {height})")
                            return (x, y, width, height)
            
            logger.warning(f"Could not find text '{target_text}' in image")
            return None
            
        except Exception as e:
            logger.error(f"Error finding text location: {e}")
            return None
    
    def replace_text_in_image(self, image_path: str, original_text: str, masked_text: str, output_path: str) -> bool:
        """
        Replace text in image at the exact location where it appears.
        
        Args:
            image_path (str): Path to input image
            original_text (str): Original Aadhaar number
            masked_text (str): Masked Aadhaar number
            output_path (str): Path to save masked image
            
        Returns:
            bool: Success status
        """
        try:
            # Load the image
            image = cv2.imread(image_path)
            if image is None:
                logger.error(f"Could not load image: {image_path}")
                return False
            
            # Find the location of the original text
            bbox = self.find_text_location_in_image(image_path, original_text)
            
            if bbox is None:
                logger.warning(f"Could not find text location, adding overlay instead")
                return self._add_overlay_text(image, masked_text, output_path)
            
            x, y, width, height = bbox
            
            # Add some padding around the text
            padding = max(5, height // 10)
            x = max(0, x - padding)
            y = max(0, y - padding)
            width = min(image.shape[1] - x, width + 2 * padding)
            height = min(image.shape[0] - y, height + 2 * padding)
            
            # Get the background color (average color of surrounding area)
            background_color = self._get_background_color(image, x, y, width, height)
            
            # Cover the original text with background color
            cv2.rectangle(image, (x, y), (x + width, y + height), background_color, -1)
            
            # Calculate appropriate font size based on the bounding box
            font_scale = self._calculate_font_scale(masked_text, width, height)
            font = cv2.FONT_HERSHEY_SIMPLEX
            thickness = max(1, int(font_scale * 2))
            
            # Calculate text position (centered in the bbox)
            text_size = cv2.getTextSize(masked_text, font, font_scale, thickness)[0]
            text_x = x + (width - text_size[0]) // 2
            text_y = y + (height + text_size[1]) // 2
            
            # Determine text color (black or white based on background)
            text_color = self._get_text_color(background_color)
            
            # Draw the masked text
            cv2.putText(image, masked_text, (text_x, text_y), font, font_scale, text_color, thickness)
            
            # Save the result
            cv2.imwrite(output_path, image)
            logger.info(f"Successfully replaced text in image. Saved to: {output_path}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error in text replacement: {e}")
            return False
    
    def _add_overlay_text(self, image: np.ndarray, masked_text: str, output_path: str) -> bool:
        """
        Add overlay text when exact location cannot be found.
        
        Args:
            image (np.ndarray): Input image
            masked_text (str): Masked text to overlay
            output_path (str): Output path
            
        Returns:
            bool: Success status
        """
        try:
            height, width = image.shape[:2]
            
            # Add semi-transparent overlay at the bottom
            overlay = image.copy()
            cv2.rectangle(overlay, (0, height - 80), (width, height), (0, 0, 0), -1)
            cv2.addWeighted(overlay, 0.7, image, 0.3, 0, image)
            
            # Add text
            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 1.2
            color = (0, 255, 0)  # Green color
            thickness = 2
            
            text = f"Masked: {masked_text}"
            text_size = cv2.getTextSize(text, font, font_scale, thickness)[0]
            text_x = (width - text_size[0]) // 2
            text_y = height - 30
            
            cv2.putText(image, text, (text_x, text_y), font, font_scale, color, thickness)
            
            # Save the result
            cv2.imwrite(output_path, image)
            logger.info(f"Added overlay text. Saved to: {output_path}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error adding overlay text: {e}")
            return False
    
    def _get_background_color(self, image: np.ndarray, x: int, y: int, width: int, height: int) -> Tuple[int, int, int]:
        """
        Get the background color around the text area.
        
        Args:
            image (np.ndarray): Input image
            x, y, width, height: Bounding box coordinates
            
        Returns:
            Tuple[int, int, int]: BGR color values
        """
        try:
            # Sample areas around the text box
            h, w = image.shape[:2]
            
            # Define sampling areas around the text
            samples = []
            
            # Above text
            if y > 10:
                samples.append(image[max(0, y-10):y, x:x+width])
            
            # Below text  
            if y + height < h - 10:
                samples.append(image[y+height:min(h, y+height+10), x:x+width])
            
            # Left of text
            if x > 10:
                samples.append(image[y:y+height, max(0, x-10):x])
            
            # Right of text
            if x + width < w - 10:
                samples.append(image[y:y+height, x+width:min(w, x+width+10)])
            
            if samples:
                # Calculate average color from all samples
                all_pixels = np.vstack([sample.reshape(-1, 3) for sample in samples if sample.size > 0])
                avg_color = np.mean(all_pixels, axis=0)
                return tuple(map(int, avg_color))
            else:
                # Fallback to white
                return (255, 255, 255)
                
        except Exception as e:
            logger.warning(f"Error getting background color: {e}, using white")
            return (255, 255, 255)
    
    def _calculate_font_scale(self, text: str, target_width: int, target_height: int) -> float:
        """
        Calculate appropriate font scale for the given text and bounding box.
        
        Args:
            text (str): Text to fit
            target_width (int): Target width
            target_height (int): Target height
            
        Returns:
            float: Calculated font scale
        """
        font = cv2.FONT_HERSHEY_SIMPLEX
        
        # Start with a base scale and adjust
        for scale in [2.0, 1.5, 1.2, 1.0, 0.8, 0.6, 0.5, 0.4]:
            thickness = max(1, int(scale * 2))
            size = cv2.getTextSize(text, font, scale, thickness)[0]
            
            # If text fits with some margin, use this scale
            if size[0] <= target_width * 0.9 and size[1] <= target_height * 0.8:
                return scale
        
        # Fallback to smallest scale
        return 0.4
    
    def _get_text_color(self, background_color: Tuple[int, int, int]) -> Tuple[int, int, int]:
        """
        Determine text color based on background color for better contrast.
        
        Args:
            background_color: BGR color tuple
            
        Returns:
            Tuple[int, int, int]: Text color (BGR)
        """
        # Calculate luminance
        b, g, r = background_color
        luminance = 0.299 * r + 0.587 * g + 0.114 * b
        
        # Use black text on light background, white text on dark background
        if luminance > 128:
            return (0, 0, 0)  # Black
        else:
            return (255, 255, 255)  # White
    
    def replace_text_at_location(self, image_path: str, original_text: str, masked_text: str, 
                                bbox: Tuple[int, int, int, int], output_path: str) -> bool:
        """
        Replace text at a specific location in the image.
        
        Args:
            image_path (str): Path to input image
            original_text (str): Original Aadhaar number
            masked_text (str): Masked Aadhaar number
            bbox (Tuple[int, int, int, int]): Bounding box (x, y, width, height)
            output_path (str): Path to save masked image
            
        Returns:
            bool: Success status
        """
        try:
            # Load the image
            image = cv2.imread(image_path)
            if image is None:
                logger.error(f"Could not load image: {image_path}")
                return False
            
            x, y, width, height = bbox
            
            # Add some padding around the text
            padding = max(5, height // 10)
            x = max(0, x - padding)
            y = max(0, y - padding)
            width = min(image.shape[1] - x, width + 2 * padding)
            height = min(image.shape[0] - y, height + 2 * padding)
            
            # Get the background color (average color of surrounding area)
            background_color = self._get_background_color(image, x, y, width, height)
            
            # Cover the original text with background color
            cv2.rectangle(image, (x, y), (x + width, y + height), background_color, -1)
            
            # Calculate appropriate font size based on the bounding box
            font_scale = self._calculate_font_scale(masked_text, width, height)
            font = cv2.FONT_HERSHEY_SIMPLEX
            thickness = max(1, int(font_scale * 2))
            
            # Calculate text position (centered in the bbox)
            text_size = cv2.getTextSize(masked_text, font, font_scale, thickness)[0]
            text_x = x + (width - text_size[0]) // 2
            text_y = y + (height + text_size[1]) // 2
            
            # Determine text color (black or white based on background)
            text_color = self._get_text_color(background_color)
            
            # Draw the masked text
            cv2.putText(image, masked_text, (text_x, text_y), font, font_scale, text_color, thickness)
            
            # Save the result
            cv2.imwrite(output_path, image)
            logger.info(f"Successfully replaced text at location. Saved to: {output_path}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error in text replacement at location: {e}")
            return False
    
    def replace_text_at_all_locations(self, image_path: str, original_text: str, masked_text: str, 
                                     bboxes: List[Tuple[int, int, int, int]], output_path: str) -> bool:
        """
        Replace text at ALL specified locations in the image.
        
        Args:
            image_path (str): Path to input image
            original_text (str): Original Aadhaar number
            masked_text (str): Masked Aadhaar number
            bboxes (List[Tuple[int, int, int, int]]): List of bounding boxes (x, y, width, height)
            output_path (str): Path to save masked image
            
        Returns:
            bool: Success status
        """
        try:
            # Load the image
            image = cv2.imread(image_path)
            if image is None:
                logger.error(f"Could not load image: {image_path}")
                return False
            
            logger.info(f"Masking Aadhaar number at {len(bboxes)} locations")
            
            # Process each location
            for i, bbox in enumerate(bboxes):
                x, y, width, height = bbox
                
                logger.info(f"Processing location {i+1}/{len(bboxes)}: ({x}, {y}, {width}, {height})")
                
                # Add some padding around the text
                padding = max(5, height // 10)
                x = max(0, x - padding)
                y = max(0, y - padding)
                width = min(image.shape[1] - x, width + 2 * padding)
                height = min(image.shape[0] - y, height + 2 * padding)
                
                # Get the background color (average color of surrounding area)
                background_color = self._get_background_color(image, x, y, width, height)
                
                # Cover the original text with background color
                cv2.rectangle(image, (x, y), (x + width, y + height), background_color, -1)
                
                # Calculate appropriate font size based on the bounding box
                font_scale = self._calculate_font_scale(masked_text, width, height)
                font = cv2.FONT_HERSHEY_SIMPLEX
                thickness = max(1, int(font_scale * 2))
                
                # Calculate text position (centered in the bbox)
                text_size = cv2.getTextSize(masked_text, font, font_scale, thickness)[0]
                text_x = x + (width - text_size[0]) // 2
                text_y = y + (height + text_size[1]) // 2
                
                # Determine text color (black or white based on background)
                text_color = self._get_text_color(background_color)
                
                # Draw the masked text
                cv2.putText(image, masked_text, (text_x, text_y), font, font_scale, text_color, thickness)
                
                logger.info(f"Masked location {i+1} with background color {background_color} and text color {text_color}")
            
            # Save the result
            cv2.imwrite(output_path, image)
            logger.info(f"Successfully replaced text at ALL {len(bboxes)} locations. Saved to: {output_path}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error in text replacement at all locations: {e}")
            return False 