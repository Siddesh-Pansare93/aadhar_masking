"""Enhanced data models for the Aadhaar UID Masking API."""

from datetime import datetime
from typing import List, Optional, Annotated
from pydantic import BaseModel, Field, validator
from bson import ObjectId
from pydantic_core import core_schema
from datetime import datetime



class _ObjectIdAnnotation:
    @classmethod
    def __get_pydantic_core_schema__(cls, _source, handler):
        return core_schema.json_or_python_schema(
            json_schema=core_schema.str_schema(),
            python_schema=core_schema.union_schema(
                [
                    core_schema.is_instance_schema(ObjectId),
                    core_schema.chain_schema([
                        core_schema.str_schema(),
                        core_schema.no_info_plain_validator_function(lambda v: ObjectId(v) if ObjectId.is_valid(v) else (_ for _ in ()).throw(ValueError("Invalid ObjectId")))
                    ])
                ]
            ),
            serialization=core_schema.plain_serializer_function_ser_schema(str),
        )






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


class EntityResponse(BaseModel) :
    name : str = Field(...)
    apiKeys : List[Annotated[ObjectId, _ObjectIdAnnotation]] 
    has_access : bool = Field(...)

class ApiResponse(BaseModel) : 
    total_req : List[Annotated[ObjectId, _ObjectIdAnnotation]]
    

class ReqResponse : 
    process_time : float  = Field(... )
    success : bool = Field(...)
    req_date  = datetime.date = Field(...)
    req_time  = datetime.time = Field(...)


