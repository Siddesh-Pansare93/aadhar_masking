"""
Secure storage manager for the Aadhaar UID Masking system.
Integrates encryption with database operations for secure file handling.
"""

import logging
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple, Union
from pathlib import Path
from bson import ObjectId
import uuid

from .database import db_manager
from .encryption import encryption
from .config import config

logger = logging.getLogger(__name__)

class SecureStorage:
    """Secure storage manager for encrypted files and records."""
    
    def __init__(self):
        """Initialize the secure storage manager."""
        self.db = db_manager
        self.encryption = encryption
    
    async def store_processed_card(
        self,
        original_image_path: str,
        masked_image_path: str,
        aadhaar_number: str,
        filename: str,
        processing_metadata: Dict[str, Any]
    ) -> ObjectId:
        """
        Store a processed Aadhaar card with encryption.
        
        Args:
            original_image_path: Path to original image
            masked_image_path: Path to masked image
            aadhaar_number: Detected Aadhaar number
            filename: Original filename
            processing_metadata: Processing statistics
            
        Returns:
            ObjectId: Created record ID
        """
        try:
            # Encrypt Aadhaar number
            encrypted_uid = encryption.encrypt_text(aadhaar_number)
            
            # Encrypt and store original image
            original_encrypted = encryption.encrypt_image_file(original_image_path)
            original_image_id = await self.db.store_encrypted_file(
                original_encrypted,
                f"original_{filename}",
                {"type": "original", "format": Path(original_image_path).suffix}
            )
            
            # Encrypt and store masked image
            masked_encrypted = encryption.encrypt_image_file(masked_image_path)
            masked_image_id = await self.db.store_encrypted_file(
                masked_encrypted,
                f"masked_{filename}",
                {"type": "masked", "format": Path(masked_image_path).suffix}
            )
            
            # Create record
            record_data = {
                "encrypted_uid": encrypted_uid,
                "original_image_id": original_image_id,
                "masked_image_id": masked_image_id,
                "filename": filename,
                "processing_metadata": processing_metadata,
                "status": "completed"
            }
            
            record_id = await self.db.create_record(record_data)
            
            logger.info(f"Stored processed card record: {record_id}")
            return record_id
            
        except Exception as e:
            logger.error(f"Failed to store processed card: {e}")
            raise Exception(f"Storage failed: {e}")
    
    async def retrieve_record_with_decrypted_uid(self, record_id: ObjectId) -> Optional[Dict[str, Any]]:
        """
        Retrieve a record and decrypt the UID for display.
        
        Args:
            record_id: Record ID
            
        Returns:
            Dict with decrypted UID or None if not found
        """
        try:
            record = await self.db.get_record(record_id)
            
            if not record:
                return None
            
            # Decrypt UID for display (masked)
            decrypted_uid = encryption.decrypt_text(record["encrypted_uid"])
            
            # Return record with decrypted UID
            result = record.copy()
            result["decrypted_uid"] = decrypted_uid
            result["uid_numbers"] = [self._mask_uid_for_display(decrypted_uid)]
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to retrieve record {record_id}: {e}")
            return None
    
    async def retrieve_encrypted_image(
        self, 
        record_id: ObjectId, 
        image_type: str
    ) -> Tuple[Optional[bytes], Optional[str], Optional[str]]:
        """
        Retrieve and decrypt an image from a record.
        
        Args:
            record_id: Record ID
            image_type: 'original' or 'masked'
            
        Returns:
            Tuple[bytes, content_type, filename]: (image_data, content_type, filename)
        """
        try:
            record = await self.db.get_record(record_id)
            
            if not record:
                logger.warning(f"Record not found: {record_id}")
                return None, None, None
            
            # Get the appropriate image ID
            if image_type == "original":
                image_id = record.get("original_image_id")
            elif image_type == "masked":
                image_id = record.get("masked_image_id")
            else:
                raise ValueError("image_type must be 'original' or 'masked'")
            
            if not image_id:
                logger.warning(f"No {image_type} image found for record {record_id}")
                return None, None, None
            
            # Retrieve encrypted file
            encrypted_data, metadata = await self.db.retrieve_encrypted_file(image_id)
            
            # Decrypt image
            decrypted_data = encryption.decrypt_image_to_bytes(encrypted_data)
            
            # Determine content type from format
            image_format = metadata.get("format", ".png").lower()
            content_type = self._get_content_type(image_format)
            
            # Generate filename
            filename = f"{image_type}_{record['filename']}"
            
            logger.debug(f"Retrieved {image_type} image for record {record_id}")
            return decrypted_data, content_type, filename
            
        except Exception as e:
            logger.error(f"Failed to retrieve {image_type} image for record {record_id}: {e}")
            return None, None, None
    
    async def list_stored_records(
        self, 
        skip: int = 0, 
        limit: int = 20,
        include_decrypted_uids: bool = True
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        List stored records with optional UID decryption.
        
        Args:
            skip: Number of records to skip
            limit: Maximum records to return
            include_decrypted_uids: Whether to decrypt UIDs for display
            
        Returns:
            Tuple[List[Dict], int]: (records, total_count)
        """
        try:
            records, total_count = await self.db.list_records(skip, limit)
            
            if include_decrypted_uids:
                # Decrypt UIDs for display
                for record in records:
                    if "encrypted_uid" in record:
                        try:
                            decrypted_uid = encryption.decrypt_text(record["encrypted_uid"])
                            record["uid_numbers"] = [self._mask_uid_for_display(decrypted_uid)]
                        except Exception as e:
                            logger.warning(f"Failed to decrypt UID for record {record['_id']}: {e}")
                            record["uid_numbers"] = ["XXXX XXXX XXXX"]  # Fallback
            
            return records, total_count
            
        except Exception as e:
            logger.error(f"Failed to list records: {e}")
            return [], 0
    
    async def search_records_by_filename(
        self, 
        search_term: str, 
        skip: int = 0, 
        limit: int = 20
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Search records by filename.
        
        Args:
            search_term: Search term for filename
            skip: Number of records to skip
            limit: Maximum records to return
            
        Returns:
            Tuple[List[Dict], int]: (matching_records, total_count)
        """
        try:
            # Create search filter
            filter_criteria = {
                "filename": {"$regex": search_term, "$options": "i"}
            }
            
            records, total_count = await self.db.list_records(skip, limit, filter_criteria)
            
            # Decrypt UIDs for display
            for record in records:
                if "encrypted_uid" in record:
                    try:
                        decrypted_uid = encryption.decrypt_text(record["encrypted_uid"])
                        record["uid_numbers"] = [self._mask_uid_for_display(decrypted_uid)]
                    except Exception as e:
                        logger.warning(f"Failed to decrypt UID for search result {record['_id']}: {e}")
                        record["uid_numbers"] = ["XXXX XXXX XXXX"]
            
            return records, total_count
            
        except Exception as e:
            logger.error(f"Failed to search records: {e}")
            return [], 0
    
    async def delete_stored_record(self, record_id: ObjectId) -> bool:
        """
        Delete a stored record and all associated encrypted files.
        
        Args:
            record_id: Record ID to delete
            
        Returns:
            bool: Deletion success status
        """
        try:
            success = await self.db.delete_record(record_id)
            
            if success:
                logger.info(f"Successfully deleted stored record: {record_id}")
            else:
                logger.warning(f"Failed to delete stored record: {record_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to delete stored record {record_id}: {e}")
            return False
    
    async def get_storage_statistics(self) -> Dict[str, Any]:
        """
        Get storage system statistics.
        
        Returns:
            Dict: Storage statistics
        """
        try:
            db_stats = await self.db.get_statistics()
            
            # Add encryption info
            encryption_info = encryption.get_encryption_info()
            
            stats = {
                **db_stats,
                "encryption_info": encryption_info,
                "storage_system": "MongoDB GridFS",
                "encryption_algorithm": "AES-Fernet"
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get storage statistics: {e}")
            return {}
    
    def _mask_uid_for_display(self, uid: str) -> str:
        """
        Mask UID for safe display (first 8 digits).
        
        Args:
            uid: Original UID
            
        Returns:
            str: Masked UID
        """
        try:
            # Remove spaces and validate
            digits_only = uid.replace(' ', '')
            if len(digits_only) != 12:
                return "XXXX XXXX XXXX"
            
            # Mask first 8 digits
            masked = 'XXXXXXXX' + digits_only[8:]
            return f"{masked[:4]} {masked[4:8]} {masked[8:12]}"
            
        except Exception:
            return "XXXX XXXX XXXX"
    
    def _get_content_type(self, file_extension: str) -> str:
        """
        Get content type from file extension.
        
        Args:
            file_extension: File extension (e.g., '.png', '.jpg')
            
        Returns:
            str: MIME content type
        """
        extension_map = {
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.gif': 'image/gif',
            '.bmp': 'image/bmp',
            '.webp': 'image/webp'
        }
        
        return extension_map.get(file_extension.lower(), 'application/octet-stream')
    
    async def cleanup_old_records(self, older_than_hours: int = 168) -> int:
        """
        Clean up old stored records.
        
        Args:
            older_than_hours: Delete records older than this many hours
            
        Returns:
            int: Number of records cleaned up
        """
        return await self.db.cleanup_old_records(older_than_hours)

# Global secure storage instance
secure_storage = SecureStorage() 