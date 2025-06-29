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

# New models for API Key management and analytics

class APIKeyCreate(BaseModel):
    """Request model for creating API keys."""
    consumer_name: str = Field(..., min_length=2, max_length=100)
    consumer_email: str = Field(..., pattern=r'^[^@]+@[^@]+\.[^@]+$')
    description: Optional[str] = Field(None, max_length=500)
    is_active: bool = Field(default=True)

class APIKeyResponse(BaseModel):
    """Response model for API key information."""
    id: str
    api_key: str
    consumer_name: str
    consumer_email: str
    description: Optional[str]
    is_active: bool
    created_at: datetime
    last_used: Optional[datetime]
    total_requests: int
    successful_requests: int
    failed_requests: int

class APIKeyListResponse(BaseModel):
    """Response model for API key list."""
    api_keys: List[APIKeyResponse]
    total_count: int
    page: int
    page_size: int
    total_pages: int

class APIKeyAnalytics(BaseModel):
    """Analytics data for an API key."""
    api_key_id: str
    consumer_name: str
    total_requests: int
    successful_requests: int
    failed_requests: int
    average_processing_time: float
    last_request: Optional[datetime]
    requests_today: int
    requests_this_week: int
    requests_this_month: int

class AdminAuth(BaseModel):
    """Admin authentication credentials."""
    username: str
    password: str

class RequestLog(BaseModel):
    """Individual request log entry."""
    timestamp: datetime
    endpoint: str
    processing_time: float
    status: str  # 'success' or 'failed'
    error_message: Optional[str]
    file_size: Optional[int]
    locations_found: Optional[int] 