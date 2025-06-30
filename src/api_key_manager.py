"""
API Key management system for the Aadhaar UID Masking service.
Handles API key generation, authentication, and analytics tracking.
"""

import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple
from bson import ObjectId
import logging

from .database import db_manager
from .config import config

logger = logging.getLogger(__name__)

class APIKeyManager:
    """Manages API keys, authentication, and analytics."""
    
    def __init__(self):
        """Initialize the API key manager."""
        self.db = db_manager
        
    async def generate_api_key(
        self, 
        consumer_name: str, 
        consumer_email: str, 
        description: Optional[str] = None
    ) -> Tuple[str, str]:
        """
        Generate a new API key for a consumer.
        
        Args:
            consumer_name: Name of the consumer
            consumer_email: Email of the consumer
            description: Optional description
            
        Returns:
            Tuple[str, str]: (api_key_id, api_key)
        """
        try:
            # Generate a secure API key
            api_key = self._generate_secure_key()
            
            # Hash the API key for storage
            key_hash = self._hash_api_key(api_key)
            
            # Create API key record
            api_key_data = {
                "key_hash": key_hash,
                "consumer_name": consumer_name,
                "consumer_email": consumer_email,
                "description": description,
                "is_active": True,
                "created_at": datetime.now(),
                "last_used": None,
                "total_requests": 0,
                "successful_requests": 0,
                "failed_requests": 0
            }
            
            # Store in database
            result = await self.db.db.api_keys.insert_one(api_key_data)
            api_key_id = str(result.inserted_id)
            
            logger.info(f"Generated API key for {consumer_name} ({consumer_email})")
            return api_key_id, api_key
            
        except Exception as e:
            logger.error(f"Failed to generate API key: {e}")
            raise Exception(f"API key generation failed: {e}")
    
    async def authenticate_api_key(self, api_key: str) -> Optional[Dict[str, Any]]:
        """
        Authenticate an API key and return consumer information.
        
        Args:
            api_key: API key to authenticate
            
        Returns:
            Optional[Dict]: Consumer data if valid, None if invalid
        """
        try:
            if not api_key:
                return None
            
            # Hash the provided key
            key_hash = self._hash_api_key(api_key)

            logger.info(f"Authenticating API key: {api_key[:8]}... (hashed: {key_hash[:8]}...)")   
            
            # Find the API key in database
            api_key_doc = await self.db.db.api_keys.find_one({
                "key_hash": key_hash,
                "is_active": True
            })

            logger.info(f"API key document found: {api_key_doc}")
            
            if not api_key_doc:
                logger.warning(f"Invalid API key attempted: {api_key[:8]}...")
                return None
            
            # Update last used timestamp
            await self.db.db.api_keys.update_one(
                {"_id": api_key_doc["_id"]},
                {"$set": {"last_used": datetime.now()}}
            )
            
            logger.debug(f"Authenticated API key for {api_key_doc['consumer_name']}")
            return api_key_doc
            
        except Exception as e:
            logger.error(f"API key authentication error: {e}")
            return None
    
    async def log_request(
        self,
        api_key_id: ObjectId,
        endpoint: str,
        processing_time: float,
        status: str,
        error_message: Optional[str] = None,
        file_size: Optional[int] = None,
        locations_found: Optional[int] = None
    ) -> None:
        """
        Log a request for analytics tracking.
        
        Args:
            api_key_id: API key object ID
            endpoint: API endpoint called
            processing_time: Request processing time
            status: 'success' or 'failed'
            error_message: Error message if failed
            file_size: Size of processed file
            locations_found: Number of locations found (for masking)
        """
        try:
            # Create request log entry
            log_entry = {
                "api_key_id": api_key_id,
                "timestamp": datetime.now(),
                "endpoint": endpoint,
                "processing_time": processing_time,
                "status": status,
                "error_message": error_message,
                "file_size": file_size,
                "locations_found": locations_found
            }
            
            # Store request log
            await self.db.db.request_logs.insert_one(log_entry)
            
            # Update API key statistics
            update_data = {
                "$inc": {"total_requests": 1}
            }
            
            if status == "success":
                update_data["$inc"]["successful_requests"] = 1
            else:
                update_data["$inc"]["failed_requests"] = 1
            
            await self.db.db.api_keys.update_one(
                {"_id": api_key_id},
                update_data
            )
            
            logger.debug(f"Logged request for API key {api_key_id}: {status}")
            
        except Exception as e:
            logger.error(f"Failed to log request: {e}")
    
    async def get_api_key_analytics(self, api_key_id: str) -> Optional[Dict[str, Any]]:
        """
        Get analytics data for a specific API key.
        
        Args:
            api_key_id: API key ID
            
        Returns:
            Optional[Dict]: Analytics data
        """
        try:
            object_id = ObjectId(api_key_id)
            
            # Get API key basic info
            api_key_doc = await self.db.db.api_keys.find_one({"_id": object_id})
            if not api_key_doc:
                return None
            
            # Calculate time ranges
            now = datetime.now()
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            week_start = today_start - timedelta(days=7)
            month_start = today_start - timedelta(days=30)
            
            # Get request counts for different time periods
            requests_today = await self.db.db.request_logs.count_documents({
                "api_key_id": object_id,
                "timestamp": {"$gte": today_start}
            })
            
            requests_this_week = await self.db.db.request_logs.count_documents({
                "api_key_id": object_id,
                "timestamp": {"$gte": week_start}
            })
            
            requests_this_month = await self.db.db.request_logs.count_documents({
                "api_key_id": object_id,
                "timestamp": {"$gte": month_start}
            })
            
            # Calculate average processing time
            pipeline = [
                {"$match": {"api_key_id": object_id, "status": "success"}},
                {"$group": {"_id": None, "avg_time": {"$avg": "$processing_time"}}}
            ]
            
            avg_result = await self.db.db.request_logs.aggregate(pipeline).to_list(1)
            avg_processing_time = avg_result[0]["avg_time"] if avg_result else 0.0
            
            # Get last request timestamp
            last_request = await self.db.db.request_logs.find_one(
                {"api_key_id": object_id},
                sort=[("timestamp", -1)]
            )
            
            analytics = {
                "api_key_id": api_key_id,
                "consumer_name": api_key_doc["consumer_name"],
                "total_requests": api_key_doc["total_requests"],
                "successful_requests": api_key_doc["successful_requests"],
                "failed_requests": api_key_doc["failed_requests"],
                "average_processing_time": round(avg_processing_time, 3),
                "last_request": last_request["timestamp"] if last_request else None,
                "requests_today": requests_today,
                "requests_this_week": requests_this_week,
                "requests_this_month": requests_this_month
            }
            
            return analytics
            
        except Exception as e:
            logger.error(f"Failed to get analytics for API key {api_key_id}: {e}")
            return None
    
    async def list_api_keys(
        self, 
        skip: int = 0, 
        limit: int = 20,
        include_inactive: bool = False
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        List all API keys with pagination.
        
        Args:
            skip: Number of records to skip
            limit: Maximum records to return
            include_inactive: Whether to include inactive keys
            
        Returns:
            Tuple[List[Dict], int]: (api_keys, total_count)
        """
        try:
            # Prepare filter
            filter_query = {} if include_inactive else {"is_active": True}
            
            # Get total count
            total_count = await self.db.db.api_keys.count_documents(filter_query)
            
            # Get API keys with pagination
            cursor = self.db.db.api_keys.find(filter_query)
            cursor = cursor.sort("created_at", -1).skip(skip).limit(limit)
            
            api_keys = await cursor.to_list(length=limit)
            
            # Remove sensitive data and add analytics
            for key_doc in api_keys:
                key_doc["id"] = str(key_doc["_id"])
                key_doc.pop("key_hash", None)  # Remove sensitive hash
                key_doc.pop("_id", None)
            
            return api_keys, total_count
            
        except Exception as e:
            logger.error(f"Failed to list API keys: {e}")
            return [], 0
    
    async def deactivate_api_key(self, api_key_id: str) -> bool:
        """
        Deactivate an API key.
        
        Args:
            api_key_id: API key ID to deactivate
            
        Returns:
            bool: Success status
        """
        try:
            # Validate ObjectId format
            try:
                object_id = ObjectId(api_key_id)
            except Exception as e:
                logger.error(f"Invalid ObjectId format for API key {api_key_id}: {e}")
                return False
            
            result = await self.db.db.api_keys.update_one(
                {"_id": object_id},
                {"$set": {"is_active": False}}
            )
            
            success = result.modified_count > 0
            if success:
                logger.info(f"Deactivated API key: {api_key_id}")
            else:
                logger.warning(f"API key not found or already deactivated: {api_key_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to deactivate API key {api_key_id}: {e}")
            return False
    
    async def reactivate_api_key(self, api_key_id: str) -> bool:
        """
        Reactivate an API key.
        
        Args:
            api_key_id: API key ID to reactivate
            
        Returns:
            bool: Success status
        """
        try:
            # Validate ObjectId format
            try:
                object_id = ObjectId(api_key_id)
            except Exception as e:
                logger.error(f"Invalid ObjectId format for API key {api_key_id}: {e}")
                return False
            
            result = await self.db.db.api_keys.update_one(
                {"_id": object_id},
                {"$set": {"is_active": True}}
            )
            
            success = result.modified_count > 0
            if success:
                logger.info(f"Reactivated API key: {api_key_id}")
            else:
                logger.warning(f"API key not found: {api_key_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to reactivate API key {api_key_id}: {e}")
            return False
    
    async def get_system_analytics(self) -> Dict[str, Any]:
        """
        Get system-wide analytics.
        
        Returns:
            Dict: System analytics
        """
        try:
            # Calculate time ranges
            now = datetime.now()
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            week_start = today_start - timedelta(days=7)
            month_start = today_start - timedelta(days=30)
            
            # Total API keys
            total_keys = await self.db.db.api_keys.count_documents({})
            active_keys = await self.db.db.api_keys.count_documents({"is_active": True})
            
            # Total requests
            total_requests = await self.db.db.request_logs.count_documents({})
            successful_requests = await self.db.db.request_logs.count_documents({"status": "success"})
            failed_requests = await self.db.db.request_logs.count_documents({"status": "failed"})
            
            # Requests by time period
            requests_today = await self.db.db.request_logs.count_documents({
                "timestamp": {"$gte": today_start}
            })
            
            requests_this_week = await self.db.db.request_logs.count_documents({
                "timestamp": {"$gte": week_start}
            })
            
            requests_this_month = await self.db.db.request_logs.count_documents({
                "timestamp": {"$gte": month_start}
            })
            
            # Average processing time
            pipeline = [
                {"$match": {"status": "success"}},
                {"$group": {"_id": None, "avg_time": {"$avg": "$processing_time"}}}
            ]
            
            avg_result = await self.db.db.request_logs.aggregate(pipeline).to_list(1)
            avg_processing_time = avg_result[0]["avg_time"] if avg_result else 0.0
            
            analytics = {
                "total_api_keys": total_keys,
                "active_api_keys": active_keys,
                "total_requests": total_requests,
                "successful_requests": successful_requests,
                "failed_requests": failed_requests,
                "success_rate": round((successful_requests / total_requests * 100) if total_requests > 0 else 0, 2),
                "requests_today": requests_today,
                "requests_this_week": requests_this_week,
                "requests_this_month": requests_this_month,
                "average_processing_time": round(avg_processing_time, 3),
                "last_updated": datetime.now()
            }
            
            return analytics
            
        except Exception as e:
            logger.error(f"Failed to get system analytics: {e}")
            return {}
    
    def _generate_secure_key(self) -> str:
        """Generate a secure API key."""
        # Generate 32 bytes of random data and encode as hex
        random_bytes = secrets.token_bytes(32)
        return random_bytes.hex()
    
    def _hash_api_key(self, api_key: str) -> str:
        """Hash an API key for secure storage."""
        # Use SHA-256 with a salt
        salt = config.SALT_KEY.encode() if config.SALT_KEY else b"default_salt"
        key_with_salt = api_key.encode() + salt
        return hashlib.sha256(key_with_salt).hexdigest()

# Global API key manager instance
api_key_manager = APIKeyManager()
