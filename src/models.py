"""Enhanced data models for the Aadhaar UID Masking API."""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, validator
from bson import ObjectId

class ProcessResult(BaseModel):
    """Response model for single image processing results."""
    filename: str
    uid_numbers: List[str]
    masked_image_url: str
    processing_time: float
    locations_found: int
    record_id: Optional[str] = None

class StoredRecordResponse(BaseModel):
    """Response model for stored records."""
    id: str
    filename: str
    uid_numbers: List[str]
    created_at: datetime
    status: str
    original_image_url: str
    masked_image_url: str

class RecordListResponse(BaseModel):
    """Response model for paginated record lists."""
    records: List[StoredRecordResponse]
    total_count: int
    page: int
    page_size: int
    total_pages: int 