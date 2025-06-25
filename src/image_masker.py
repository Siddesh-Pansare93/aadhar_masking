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
    Class for masking the first 8 digits of Aadhaar numbers in images.
    """
    
    def __init__(self):
        """Initialize the image masker."""
        self.ocr_reader = easyocr.Reader(['en'])
    
    def mask_aadhaar_number(self, aadhaar_number: str) -> str:
        """
        Mask the first 8 digits of an Aadhaar number with 'X'.
        
        Args:
            aadhaar_number (str): Original Aadhaar number (e.g., "1234 5678 9012")
            
        Returns:
            str: Masked Aadhaar number (e.g., "XXXX XXXX 9012")
        """
        if not aadhaar_number or len(aadhaar_number.replace(' ', '')) != 12:
            raise ValueError("Invalid Aadhaar number format")
        
        # Remove spaces and mask first 8 digits
        digits_only = aadhaar_number.replace(' ', '')
        masked = 'XXXXXXXX' + digits_only[8:]
        
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
            
            # Create a smooth background rectangle with blending
            self._draw_blended_rectangle(image, x, y, width, height, background_color)
            
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
        Get the background color around the text area using advanced sampling.
        
        Args:
            image (np.ndarray): Input image
            x, y, width, height: Bounding box coordinates
            
        Returns:
            Tuple[int, int, int]: BGR color values
        """
        try:
            h, w = image.shape[:2]
            
            # Create a larger sampling area around the text
            padding = max(15, min(width, height) // 2)
            
            # Define multiple sampling regions for better color detection
            samples = []
            
            # Sample points around the perimeter of the text box
            sample_points = []
            
            # Top edge samples
            if y > padding:
                for i in range(max(1, width // 10)):
                    sample_x = x + (i * width // max(1, width // 10))
                    sample_y = y - padding // 2
                    if 0 <= sample_x < w and 0 <= sample_y < h:
                        sample_points.append((sample_x, sample_y))
            
            # Bottom edge samples
            if y + height + padding < h:
                for i in range(max(1, width // 10)):
                    sample_x = x + (i * width // max(1, width // 10))
                    sample_y = y + height + padding // 2
                    if 0 <= sample_x < w and 0 <= sample_y < h:
                        sample_points.append((sample_x, sample_y))
            
            # Left edge samples
            if x > padding:
                for i in range(max(1, height // 10)):
                    sample_x = x - padding // 2
                    sample_y = y + (i * height // max(1, height // 10))
                    if 0 <= sample_x < w and 0 <= sample_y < h:
                        sample_points.append((sample_x, sample_y))
            
            # Right edge samples
            if x + width + padding < w:
                for i in range(max(1, height // 10)):
                    sample_x = x + width + padding // 2
                    sample_y = y + (i * height // max(1, height // 10))
                    if 0 <= sample_x < w and 0 <= sample_y < h:
                        sample_points.append((sample_x, sample_y))
            
            # Collect color samples from multiple points with small windows
            window_size = 3
            color_samples = []
            
            for px, py in sample_points:
                # Sample a small window around each point
                y1 = max(0, py - window_size)
                y2 = min(h, py + window_size + 1)
                x1 = max(0, px - window_size)
                x2 = min(w, px + window_size + 1)
                
                window = image[y1:y2, x1:x2]
                if window.size > 0:
                    # Get median color from this window (more robust than mean)
                    window_pixels = window.reshape(-1, 3)
                    median_color = np.median(window_pixels, axis=0)
                    color_samples.append(median_color)
            
            if color_samples:
                # Use median of all samples for final color (robust against outliers)
                color_samples = np.array(color_samples)
                final_color = np.median(color_samples, axis=0)
                return tuple(map(int, final_color))
            
            # Fallback: sample larger areas if points didn't work
            fallback_samples = []
            
            # Above text (larger area)
            if y > padding:
                area = image[max(0, y-padding):y, x:x+width]
                if area.size > 0:
                    fallback_samples.append(area)
            
            # Below text (larger area)
            if y + height + padding < h:
                area = image[y+height:min(h, y+height+padding), x:x+width]
                if area.size > 0:
                    fallback_samples.append(area)
            
            # Left of text (larger area)
            if x > padding:
                area = image[y:y+height, max(0, x-padding):x]
                if area.size > 0:
                    fallback_samples.append(area)
            
            # Right of text (larger area)
            if x + width + padding < w:
                area = image[y:y+height, x+width:min(w, x+width+padding)]
                if area.size > 0:
                    fallback_samples.append(area)
            
            if fallback_samples:
                # Calculate median color from all fallback samples
                all_pixels = np.vstack([sample.reshape(-1, 3) for sample in fallback_samples])
                median_color = np.median(all_pixels, axis=0)
                return tuple(map(int, median_color))
            
            # Final fallback - sample the immediate border
            border_pixels = []
            
            # Sample immediate border pixels
            for dy in [-1, 0, 1]:
                for dx in [-1, 0, 1]:
                    if dx == 0 and dy == 0:
                        continue
                    
                    border_y = y + dy
                    border_x = x + dx
                    
                    if 0 <= border_y < h and 0 <= border_x < w:
                        border_pixels.append(image[border_y, border_x])
            
            if border_pixels:
                border_pixels = np.array(border_pixels)
                avg_color = np.mean(border_pixels, axis=0)
                return tuple(map(int, avg_color))
            
            # Ultimate fallback
            return (240, 240, 240)  # Light gray instead of pure white
                
        except Exception as e:
            logger.warning(f"Error getting background color: {e}, using light gray")
            return (240, 240, 240)
    
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

    def _draw_blended_rectangle(self, image: np.ndarray, x: int, y: int, width: int, height: int, background_color: Tuple[int, int, int]) -> None:
        """
        Draw a rectangle with blended edges for seamless background integration.
        
        Args:
            image (np.ndarray): Input image to modify
            x, y, width, height: Rectangle coordinates
            background_color: BGR color tuple
        """
        try:
            h, w = image.shape[:2]
            
            # Ensure coordinates are within image bounds
            x = max(0, min(x, w - 1))
            y = max(0, min(y, h - 1))
            width = min(width, w - x)
            height = min(height, h - y)
            
            if width <= 0 or height <= 0:
                return
            
            # Create a mask for the rectangle area
            mask = np.zeros((h, w), dtype=np.uint8)
            cv2.rectangle(mask, (x, y), (x + width, y + height), 255, -1)
            
            # Apply slight blur to the mask edges for smoother blending
            kernel_size = max(3, min(width, height) // 10)
            if kernel_size % 2 == 0:
                kernel_size += 1
            
            # Create a slightly blurred mask for edge blending
            blurred_mask = cv2.GaussianBlur(mask, (kernel_size, kernel_size), 0)
            blurred_mask = blurred_mask.astype(np.float32) / 255.0
            
            # Sample the actual background around the edges for gradient blending
            edge_colors = self._sample_edge_colors(image, x, y, width, height)
            
            # Create the replacement rectangle
            replacement = np.full((h, w, 3), background_color, dtype=np.uint8)
            
            # Add slight color variation based on edge samples
            if edge_colors:
                # Create a gradient effect
                for i, (edge_x, edge_y, edge_color) in enumerate(edge_colors):
                    # Calculate distance from each pixel to this edge sample
                    for py in range(max(0, y - 5), min(h, y + height + 5)):
                        for px in range(max(0, x - 5), min(w, x + width + 5)):
                            if x <= px < x + width and y <= py < y + height:
                                # Distance to edge sample
                                dist = np.sqrt((px - edge_x) ** 2 + (py - edge_y) ** 2)
                                
                                # Blend factor based on distance (closer = more influence)
                                if dist < min(width, height) / 2:
                                    blend_factor = max(0, 1 - (dist / (min(width, height) / 2))) * 0.3
                                    
                                    # Blend the color
                                    for c in range(3):
                                        current_val = replacement[py, px, c]
                                        edge_val = edge_color[c]
                                        replacement[py, px, c] = int(current_val * (1 - blend_factor) + edge_val * blend_factor)
            
            # Apply the replacement with smooth blending
            for c in range(3):
                image[:, :, c] = (image[:, :, c] * (1 - blurred_mask) + 
                                replacement[:, :, c] * blurred_mask).astype(np.uint8)
            
        except Exception as e:
            logger.warning(f"Error in blended rectangle drawing: {e}, falling back to simple rectangle")
            cv2.rectangle(image, (x, y), (x + width, y + height), background_color, -1)

    def _sample_edge_colors(self, image: np.ndarray, x: int, y: int, width: int, height: int) -> List[Tuple[int, int, Tuple[int, int, int]]]:
        """
        Sample colors from the edges of the rectangle for gradient blending.
        
        Args:
            image (np.ndarray): Input image
            x, y, width, height: Rectangle coordinates
            
        Returns:
            List of (edge_x, edge_y, color) tuples
        """
        edge_samples = []
        h, w = image.shape[:2]
        
        try:
            # Sample from top edge
            if y > 0:
                for i in range(0, width, max(1, width // 5)):
                    edge_x = x + i
                    edge_y = y - 1
                    if 0 <= edge_x < w and 0 <= edge_y < h:
                        color = tuple(map(int, image[edge_y, edge_x]))
                        edge_samples.append((edge_x, edge_y, color))
            
            # Sample from bottom edge
            if y + height < h:
                for i in range(0, width, max(1, width // 5)):
                    edge_x = x + i
                    edge_y = y + height
                    if 0 <= edge_x < w and 0 <= edge_y < h:
                        color = tuple(map(int, image[edge_y, edge_x]))
                        edge_samples.append((edge_x, edge_y, color))
            
            # Sample from left edge
            if x > 0:
                for i in range(0, height, max(1, height // 5)):
                    edge_x = x - 1
                    edge_y = y + i
                    if 0 <= edge_x < w and 0 <= edge_y < h:
                        color = tuple(map(int, image[edge_y, edge_x]))
                        edge_samples.append((edge_x, edge_y, color))
            
            # Sample from right edge
            if x + width < w:
                for i in range(0, height, max(1, height // 5)):
                    edge_x = x + width
                    edge_y = y + i
                    if 0 <= edge_x < w and 0 <= edge_y < h:
                        color = tuple(map(int, image[edge_y, edge_x]))
                        edge_samples.append((edge_x, edge_y, color))
        
        except Exception as e:
            logger.warning(f"Error sampling edge colors: {e}")
        
        return edge_samples
    
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
            
            # Create a smooth background rectangle with blending
            self._draw_blended_rectangle(image, x, y, width, height, background_color)
            
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
                
                # Create a smooth background rectangle with blending
                self._draw_blended_rectangle(image, x, y, width, height, background_color)
                
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