"""
Database management for the Aadhaar UID Masking system.
Handles MongoDB operations with Motor async driver and GridFS for encrypted file storage.
"""

import logging
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple
from bson import ObjectId
import asyncio

import motor.motor_asyncio
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo.errors import ConnectionFailure, DuplicateKeyError
import gridfs
import gridfs.errors

from .config import config
from .encryption import encryption

logger = logging.getLogger(__name__)

# Custom exception for GridFS operations
class GridFSFileNotFound(Exception):
    """Exception raised when a GridFS file is not found."""
    pass

class SimpleGridFSWrapper:
    """Simple wrapper for GridFS operations when AsyncIOMotorGridFS is not available."""
    
    def __init__(self, db, collection_name):
        self.db = db
        self.collection_name = collection_name
        self.files_collection = db[f"{collection_name}.files"]
        self.chunks_collection = db[f"{collection_name}.chunks"]
    
    async def put(self, data, **metadata):
        """Store data in GridFS-like structure."""
        file_id = ObjectId()
        
        # Store metadata
        file_doc = {
            "_id": file_id,
            "length": len(data),
            "chunkSize": 255 * 1024,  # 255KB chunks
            "uploadDate": datetime.now(),
            **metadata
        }
        
        await self.files_collection.insert_one(file_doc)
        
        # Store data in chunks
        chunk_size = 255 * 1024
        for i, chunk_start in enumerate(range(0, len(data), chunk_size)):
            chunk_data = data[chunk_start:chunk_start + chunk_size]
            chunk_doc = {
                "_id": ObjectId(),
                "files_id": file_id,
                "n": i,
                "data": chunk_data
            }
            await self.chunks_collection.insert_one(chunk_doc)
        
        return file_id
    
    async def get(self, file_id):
        """Retrieve data from GridFS-like structure."""
        # Get file metadata
        file_doc = await self.files_collection.find_one({"_id": file_id})
        if not file_doc:
            raise GridFSFileNotFound(f"No file found with id {file_id}")
        
        # Get chunks
        chunks_cursor = self.chunks_collection.find({"files_id": file_id}).sort("n", 1)
        chunks = await chunks_cursor.to_list(None)
        
        # Reconstruct data
        data = b"".join([chunk["data"] for chunk in chunks])
        
        # Create a simple object with read method
        class GridOut:
            def __init__(self, data, metadata):
                self._data = data
                self.filename = metadata.get("filename", "")
                self.upload_date = metadata.get("uploadDate", datetime.now())
                self.length = len(data)
                self.metadata = {k: v for k, v in metadata.items() 
                               if k not in ["_id", "length", "chunkSize", "uploadDate"]}
            
            async def read(self):
                return self._data
        
        return GridOut(data, file_doc)
    
    async def delete(self, file_id):
        """Delete file from GridFS-like structure."""
        # Delete file metadata
        result1 = await self.files_collection.delete_one({"_id": file_id})
        # Delete chunks
        result2 = await self.chunks_collection.delete_many({"files_id": file_id})
        
        if result1.deleted_count == 0:
            raise GridFSFileNotFound(f"No file found with id {file_id}")

class DatabaseManager:
    """Async database manager for MongoDB operations."""
    
    def __init__(self):
        """Initialize the database manager."""
        self.client: Optional[AsyncIOMotorClient] = None
        self.db: Optional[AsyncIOMotorDatabase] = None
        self.gridfs = None
        self._connection_validated = False
    
    async def connect(self) -> bool:
        """Connect to MongoDB database."""
        try:
            self.client = AsyncIOMotorClient(config.MONGODB_URL)
            self.db = self.client[config.DATABASE_NAME]
            # Try different GridFS approaches based on Motor version
            try:
                # Method 1: Direct AsyncIOMotorGridFS (newer Motor versions)
                self.gridfs = motor.motor_asyncio.AsyncIOMotorGridFS(self.db, collection=config.GRID_FS_BUCKET)
            except AttributeError:
                # Method 2: Use GridFS with the database delegate (fallback)
                try:
                    import gridfs
                    self.gridfs = gridfs.GridFS(self.db.delegate, collection=config.GRID_FS_BUCKET)
                    logger.info("Using GridFS fallback method")
                except Exception as e:
                    logger.warning(f"GridFS initialization failed: {e}")
                    # Method 3: Create a simple GridFS wrapper
                    self.gridfs = SimpleGridFSWrapper(self.db, config.GRID_FS_BUCKET)
            
            # Test connection
            await self.client.admin.command('ping')
            self._connection_validated = True
            logger.info(f"Connected to MongoDB: {config.DATABASE_NAME}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            return False
    
    async def disconnect(self) -> None:
        """Disconnect from MongoDB."""
        if self.client:
            self.client.close()
            self._connection_validated = False
            logger.info("Disconnected from MongoDB")
    
    async def _create_indexes(self) -> None:
        """Create database indexes for optimal performance."""
        try:
            # Index on created_at for time-based queries
            await self.db.processed_cards.create_index([("created_at", -1)])
            
            # Index on filename for search
            await self.db.processed_cards.create_index([("filename", 1)])
            
            # Index on status for filtering
            await self.db.processed_cards.create_index([("status", 1)])
            
            # Compound index for pagination
            await self.db.processed_cards.create_index([("created_at", -1), ("_id", 1)])
            
            logger.info("Database indexes created successfully")
            
        except Exception as e:
            logger.warning(f"Could not create all indexes: {e}")
    
    def _validate_connection(self) -> None:
        """Validate that database connection is active."""
        if not self._connection_validated or self.db is None or self.gridfs is None:
            raise ConnectionError("Database not connected. Call connect() first.")
    
    async def store_encrypted_file(self, file_data: bytes, filename: str, metadata: Dict[str, Any] = None) -> ObjectId:
        """
        Store encrypted file data in GridFS.
        
        Args:
            file_data (bytes): Encrypted file data
            filename (str): Original filename
            metadata (dict): Additional metadata
            
        Returns:
            ObjectId: GridFS file ID
            
        Raises:
            Exception: If storage fails
        """
        self._validate_connection()
        
        try:
            # Prepare metadata
            file_metadata = {
                "filename": filename,
                "upload_date": datetime.now(),
                "encrypted": True,
                **(metadata or {})
            }
            
            # Store in GridFS - handle different GridFS types
            if hasattr(self.gridfs, 'put') and hasattr(self.gridfs.put, '__call__'):
                # Check if it's our async SimpleGridFSWrapper or AsyncIOMotorGridFS
                if isinstance(self.gridfs, SimpleGridFSWrapper):
                    file_id = await self.gridfs.put(file_data, **file_metadata)
                else:
                    # Try async first, fallback to sync
                    try:
                        file_id = await self.gridfs.put(file_data, **file_metadata)
                    except TypeError:
                        # Synchronous GridFS
                        file_id = self.gridfs.put(file_data, **file_metadata)
            else:
                raise Exception("GridFS not properly initialized")
            
            logger.info(f"Stored encrypted file: {filename} (ID: {file_id})")
            return file_id
            
        except Exception as e:
            logger.error(f"Failed to store encrypted file {filename}: {e}")
            raise Exception(f"File storage failed: {e}")
    
    async def retrieve_encrypted_file(self, file_id: ObjectId) -> Tuple[bytes, Dict[str, Any]]:
        """
        Retrieve encrypted file data from GridFS.
        
        Args:
            file_id (ObjectId): GridFS file ID
            
        Returns:
            Tuple[bytes, Dict]: (file_data, metadata)
            
        Raises:
            Exception: If retrieval fails
        """
        self._validate_connection()
        
        try:
            # Get file from GridFS - handle different GridFS types
            if isinstance(self.gridfs, SimpleGridFSWrapper):
                grid_out = await self.gridfs.get(file_id)
                file_data = await grid_out.read()
            else:
                # Try async first, fallback to sync
                try:
                    grid_out = await self.gridfs.get(file_id)
                    file_data = await grid_out.read()
                except TypeError:
                    # Synchronous GridFS
                    grid_out = self.gridfs.get(file_id)
                    file_data = grid_out.read()
            
            # Get metadata
            metadata = {
                "filename": grid_out.filename,
                "upload_date": grid_out.upload_date,
                "length": grid_out.length,
                **grid_out.metadata
            }
            
            logger.debug(f"Retrieved encrypted file: {file_id}")
            return file_data, metadata
            
        except (gridfs.errors.NoFile, GridFSFileNotFound):
            logger.error(f"File not found: {file_id}")
            raise Exception(f"File not found: {file_id}")
        except Exception as e:
            logger.error(f"Failed to retrieve file {file_id}: {e}")
            raise Exception(f"File retrieval failed: {e}")
    
    async def delete_encrypted_file(self, file_id: ObjectId) -> bool:
        """
        Delete encrypted file from GridFS.
        
        Args:
            file_id (ObjectId): GridFS file ID
            
        Returns:
            bool: Deletion success status
        """
        self._validate_connection()
        
        try:
            # Delete from GridFS - handle different GridFS types
            if isinstance(self.gridfs, SimpleGridFSWrapper):
                await self.gridfs.delete(file_id)
            else:
                # Try async first, fallback to sync
                try:
                    await self.gridfs.delete(file_id)
                except TypeError:
                    # Synchronous GridFS
                    self.gridfs.delete(file_id)
            
            logger.info(f"Deleted encrypted file: {file_id}")
            return True
            
        except (gridfs.errors.NoFile, GridFSFileNotFound):
            logger.warning(f"File not found for deletion: {file_id}")
            return False
        except Exception as e:
            logger.error(f"Failed to delete file {file_id}: {e}")
            return False
    
    async def create_record(self, record_data: Dict[str, Any]) -> ObjectId:
        """
        Create a new processed card record.
        
        Args:
            record_data (dict): Record data
            
        Returns:
            ObjectId: Created record ID
            
        Raises:
            Exception: If creation fails
        """
        self._validate_connection()
        
        try:
            # Add timestamps
            record_data["created_at"] = datetime.now()
            record_data["updated_at"] = datetime.now()
            
            # Insert record
            result = await self.db.processed_cards.insert_one(record_data)
            
            logger.info(f"Created record: {result.inserted_id}")
            return result.inserted_id
            
        except Exception as e:
            logger.error(f"Failed to create record: {e}")
            raise Exception(f"Record creation failed: {e}")
    
    async def get_record(self, record_id: ObjectId) -> Optional[Dict[str, Any]]:
        """
        Retrieve a record by ID.
        
        Args:
            record_id (ObjectId): Record ID
            
        Returns:
            Optional[Dict]: Record data if found
        """
        self._validate_connection()
        
        try:
            record = await self.db.processed_cards.find_one({"_id": record_id})
            
            if record:
                logger.debug(f"Retrieved record: {record_id}")
            
            return record
            
        except Exception as e:
            logger.error(f"Failed to retrieve record {record_id}: {e}")
            return None
    
    async def update_record(self, record_id: ObjectId, update_data: Dict[str, Any]) -> bool:
        """
        Update a record.
        
        Args:
            record_id (ObjectId): Record ID
            update_data (dict): Data to update
            
        Returns:
            bool: Update success status
        """
        self._validate_connection()
        
        try:
            # Add update timestamp
            update_data["updated_at"] = datetime.now()
            
            # Update record
            result = await self.db.processed_cards.update_one(
                {"_id": record_id},
                {"$set": update_data}
            )
            
            success = result.modified_count > 0
            
            if success:
                logger.info(f"Updated record: {record_id}")
            else:
                logger.warning(f"No record updated: {record_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to update record {record_id}: {e}")
            return False
    
    async def delete_record(self, record_id: ObjectId) -> bool:
        """
        Delete a record and its associated files.
        
        Args:
            record_id (ObjectId): Record ID
            
        Returns:
            bool: Deletion success status
        """
        self._validate_connection()
        
        try:
            # Get record to find associated files
            record = await self.get_record(record_id)
            
            if not record:
                logger.warning(f"Record not found for deletion: {record_id}")
                return False
            
            # Delete associated files
            files_deleted = True
            
            if "original_image_id" in record and record["original_image_id"]:
                files_deleted &= await self.delete_encrypted_file(record["original_image_id"])
            
            if "masked_image_id" in record and record["masked_image_id"]:
                files_deleted &= await self.delete_encrypted_file(record["masked_image_id"])
            
            # Delete record
            result = await self.db.processed_cards.delete_one({"_id": record_id})
            record_deleted = result.deleted_count > 0
            
            if record_deleted:
                logger.info(f"Deleted record: {record_id}")
            
            return record_deleted and files_deleted
            
        except Exception as e:
            logger.error(f"Failed to delete record {record_id}: {e}")
            return False
    
    async def list_records(self, skip: int = 0, limit: int = 20, 
                          filter_criteria: Dict[str, Any] = None) -> Tuple[List[Dict[str, Any]], int]:
        """
        List records with pagination and filtering.
        
        Args:
            skip (int): Number of records to skip
            limit (int): Maximum number of records to return
            filter_criteria (dict): MongoDB filter criteria
            
        Returns:
            Tuple[List[Dict], int]: (records, total_count)
        """
        self._validate_connection()
        
        try:
            # Prepare filter
            filter_query = filter_criteria or {}
            
            # Get total count
            total_count = await self.db.processed_cards.count_documents(filter_query)
            
            # Get records with pagination
            cursor = self.db.processed_cards.find(filter_query)
            cursor = cursor.sort("created_at", -1).skip(skip).limit(limit)
            
            records = await cursor.to_list(length=limit)
            
            logger.debug(f"Listed {len(records)} records (skip: {skip}, limit: {limit})")
            return records, total_count
            
        except Exception as e:
            logger.error(f"Failed to list records: {e}")
            return [], 0
    
    async def search_records(self, search_term: str, skip: int = 0, limit: int = 20) -> Tuple[List[Dict[str, Any]], int]:
        """
        Search records by filename or other searchable fields.
        
        Args:
            search_term (str): Search term
            skip (int): Number of records to skip
            limit (int): Maximum number of records to return
            
        Returns:
            Tuple[List[Dict], int]: (records, total_count)
        """
        # Create search filter
        search_filter = {
            "$or": [
                {"filename": {"$regex": search_term, "$options": "i"}},
                {"status": {"$regex": search_term, "$options": "i"}}
            ]
        }
        
        return await self.list_records(skip, limit, search_filter)
    
    async def get_statistics(self) -> Dict[str, Any]:
        """
        Get database statistics.
        
        Returns:
            Dict: Database statistics
        """
        self._validate_connection()
        
        try:
            # Total records
            total_records = await self.db.processed_cards.count_documents({})
            
            # Status distribution
            status_pipeline = [
                {"$group": {"_id": "$status", "count": {"$sum": 1}}}
            ]
            status_stats = await self.db.processed_cards.aggregate(status_pipeline).to_list(None)
            
            # Recent activity (last 24 hours)
            from datetime import timedelta
            recent_cutoff = datetime.now() - timedelta(hours=24)
            recent_records = await self.db.processed_cards.count_documents({
                "created_at": {"$gte": recent_cutoff}
            })
            
            # GridFS statistics
            gridfs_stats = await self.db.command("collstats", f"{config.GRID_FS_BUCKET}.files")
            
            stats = {
                "total_records": total_records,
                "status_distribution": {stat["_id"]: stat["count"] for stat in status_stats},
                "recent_activity_24h": recent_records,
                "gridfs_files": gridfs_stats.get("count", 0),
                "gridfs_size_bytes": gridfs_stats.get("size", 0),
                "last_updated": datetime.now()
            }
            
            logger.debug("Generated database statistics")
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get statistics: {e}")
            return {}
    
    async def cleanup_old_records(self, older_than_hours: int = 168) -> int:  # Default: 1 week
        """
        Clean up old records and associated files.
        
        Args:
            older_than_hours (int): Delete records older than this many hours
            
        Returns:
            int: Number of records cleaned up
        """
        self._validate_connection()
        
        try:
            from datetime import timedelta
            cutoff_date = datetime.now() - timedelta(hours=older_than_hours)
            
            # Find old records
            old_records = await self.db.processed_cards.find({
                "created_at": {"$lt": cutoff_date}
            }).to_list(None)
            
            cleaned_count = 0
            
            for record in old_records:
                if await self.delete_record(record["_id"]):
                    cleaned_count += 1
            
            logger.info(f"Cleaned up {cleaned_count} old records")
            return cleaned_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup old records: {e}")
            return 0

# Global database manager instance
db_manager = DatabaseManager() 