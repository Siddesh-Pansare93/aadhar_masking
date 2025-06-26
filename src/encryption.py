"""
Encryption utilities for the Aadhaar UID Masking system.
Provides secure AES encryption for images and UIDs using Fernet.
"""

import os
import io
from typing import Optional, Union, Tuple
from pathlib import Path
import logging

from cryptography.fernet import Fernet, InvalidToken
from PIL import Image
import numpy as np
import cv2

from .config import config

logger = logging.getLogger(__name__)

class ImageEncryption:
    """Handle encryption and decryption of images and UIDs."""
    
    def __init__(self):
        """Initialize the encryption handler."""
        try:
            key = config.get_fernet_key()
            self.fernet = Fernet(key)
            logger.info("Encryption system initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize encryption: {e}")
            raise
    
    def encrypt_text(self, text: str) -> bytes:
        """
        Encrypt a text string (like UID).
        
        Args:
            text (str): Text to encrypt
            
        Returns:
            bytes: Encrypted text
            
        Raises:
            Exception: If encryption fails
        """
        try:
            text_bytes = text.encode('utf-8')
            encrypted_bytes = self.fernet.encrypt(text_bytes)
            logger.debug(f"Successfully encrypted text of length {len(text)}")
            return encrypted_bytes
        except Exception as e:
            logger.error(f"Failed to encrypt text: {e}")
            raise Exception(f"Encryption failed: {e}")
    
    def decrypt_text(self, encrypted_text: bytes) -> str:
        """
        Decrypt encrypted text.
        
        Args:
            encrypted_text (bytes): Encrypted text bytes
            
        Returns:
            str: Decrypted text
            
        Raises:
            Exception: If decryption fails
        """
        try:
            decrypted_bytes = self.fernet.decrypt(encrypted_text)
            text = decrypted_bytes.decode('utf-8')
            logger.debug(f"Successfully decrypted text of length {len(text)}")
            return text
        except InvalidToken:
            logger.error("Invalid token - decryption failed")
            raise Exception("Invalid decryption key or corrupted data")
        except Exception as e:
            logger.error(f"Failed to decrypt text: {e}")
            raise Exception(f"Decryption failed: {e}")
    
    def encrypt_image_file(self, image_path: Union[str, Path]) -> bytes:
        """
        Encrypt an image file.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            bytes: Encrypted image data
            
        Raises:
            Exception: If encryption fails
        """
        try:
            image_path = Path(image_path)
            
            if not image_path.exists():
                raise FileNotFoundError(f"Image file not found: {image_path}")
            
            # Read image file as bytes
            with open(image_path, 'rb') as f:
                image_bytes = f.read()
            
            # Encrypt the image data
            encrypted_bytes = self.fernet.encrypt(image_bytes)
            
            logger.info(f"Successfully encrypted image: {image_path.name} ({len(image_bytes)} -> {len(encrypted_bytes)} bytes)")
            return encrypted_bytes
            
        except Exception as e:
            logger.error(f"Failed to encrypt image {image_path}: {e}")
            raise Exception(f"Image encryption failed: {e}")
    
    def decrypt_image_to_bytes(self, encrypted_image: bytes) -> bytes:
        """
        Decrypt encrypted image data to original image bytes.
        
        Args:
            encrypted_image (bytes): Encrypted image data
            
        Returns:
            bytes: Original image data
            
        Raises:
            Exception: If decryption fails
        """
        try:
            decrypted_bytes = self.fernet.decrypt(encrypted_image)
            logger.debug(f"Successfully decrypted image data ({len(encrypted_image)} -> {len(decrypted_bytes)} bytes)")
            return decrypted_bytes
        except InvalidToken:
            logger.error("Invalid token - image decryption failed")
            raise Exception("Invalid decryption key or corrupted image data")
        except Exception as e:
            logger.error(f"Failed to decrypt image: {e}")
            raise Exception(f"Image decryption failed: {e}")
    
    def decrypt_image_to_file(self, encrypted_image: bytes, output_path: Union[str, Path]) -> bool:
        """
        Decrypt encrypted image and save to file.
        
        Args:
            encrypted_image (bytes): Encrypted image data
            output_path: Path where to save the decrypted image
            
        Returns:
            bool: Success status
        """
        try:
            output_path = Path(output_path)
            
            # Decrypt image data
            decrypted_bytes = self.decrypt_image_to_bytes(encrypted_image)
            
            # Create output directory if it doesn't exist
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write decrypted data to file
            with open(output_path, 'wb') as f:
                f.write(decrypted_bytes)
            
            logger.info(f"Successfully saved decrypted image to: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save decrypted image to {output_path}: {e}")
            return False
    
    def encrypt_image_from_array(self, image_array: np.ndarray, format: str = 'PNG') -> bytes:
        """
        Encrypt an image from a numpy array.
        
        Args:
            image_array (np.ndarray): Image as numpy array
            format (str): Image format (PNG, JPEG, etc.)
            
        Returns:
            bytes: Encrypted image data
            
        Raises:
            Exception: If encryption fails
        """
        try:
            # Convert array to image format
            if format.upper() == 'PNG':
                # Convert BGR to RGB for PIL
                if len(image_array.shape) == 3 and image_array.shape[2] == 3:
                    image_array = cv2.cvtColor(image_array, cv2.COLOR_BGR2RGB)
                
                # Create PIL image
                pil_image = Image.fromarray(image_array)
                
                # Save to bytes buffer
                buffer = io.BytesIO()
                pil_image.save(buffer, format='PNG')
                image_bytes = buffer.getvalue()
            
            elif format.upper() == 'JPEG' or format.upper() == 'JPG':
                # Convert BGR to RGB for PIL
                if len(image_array.shape) == 3 and image_array.shape[2] == 3:
                    image_array = cv2.cvtColor(image_array, cv2.COLOR_BGR2RGB)
                
                # Create PIL image
                pil_image = Image.fromarray(image_array)
                
                # Save to bytes buffer
                buffer = io.BytesIO()
                pil_image.save(buffer, format='JPEG', quality=95)
                image_bytes = buffer.getvalue()
            
            else:
                # Use OpenCV for other formats
                _, encoded_image = cv2.imencode(f'.{format.lower()}', image_array)
                image_bytes = encoded_image.tobytes()
            
            # Encrypt the image bytes
            encrypted_bytes = self.fernet.encrypt(image_bytes)
            
            logger.debug(f"Successfully encrypted {format} image from array ({len(image_bytes)} -> {len(encrypted_bytes)} bytes)")
            return encrypted_bytes
            
        except Exception as e:
            logger.error(f"Failed to encrypt image from array: {e}")
            raise Exception(f"Array encryption failed: {e}")
    
    def decrypt_image_to_array(self, encrypted_image: bytes) -> np.ndarray:
        """
        Decrypt encrypted image and return as numpy array.
        
        Args:
            encrypted_image (bytes): Encrypted image data
            
        Returns:
            np.ndarray: Image as numpy array (BGR format for OpenCV)
            
        Raises:
            Exception: If decryption fails
        """
        try:
            # Decrypt image data
            decrypted_bytes = self.decrypt_image_to_bytes(encrypted_image)
            
            # Convert bytes to numpy array
            nparr = np.frombuffer(decrypted_bytes, np.uint8)
            
            # Decode image
            image_array = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if image_array is None:
                raise Exception("Failed to decode decrypted image data")
            
            logger.debug(f"Successfully decrypted image to array (shape: {image_array.shape})")
            return image_array
            
        except Exception as e:
            logger.error(f"Failed to decrypt image to array: {e}")
            raise Exception(f"Array decryption failed: {e}")
    
    def validate_encryption(self, original_data: Union[str, bytes], encrypted_data: bytes) -> bool:
        """
        Validate that encryption/decryption works correctly.
        
        Args:
            original_data: Original data (text or bytes)
            encrypted_data: Encrypted data
            
        Returns:
            bool: True if validation successful
        """
        try:
            if isinstance(original_data, str):
                decrypted = self.decrypt_text(encrypted_data)
                return decrypted == original_data
            elif isinstance(original_data, bytes):
                decrypted = self.decrypt_image_to_bytes(encrypted_data)
                return decrypted == original_data
            else:
                return False
                
        except Exception as e:
            logger.error(f"Validation failed: {e}")
            return False
    
    def get_encryption_info(self) -> dict:
        """
        Get information about the encryption system.
        
        Returns:
            dict: Encryption system information
        """
        return {
            "algorithm": "AES",
            "mode": "Fernet (AES-128 in CBC mode)",
            "key_derivation": "PBKDF2-HMAC-SHA256",
            "status": "initialized",
            "environment": config.ENVIRONMENT
        }

# Global encryption instance
encryption = ImageEncryption() 