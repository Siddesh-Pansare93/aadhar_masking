#!/usr/bin/env python3
"""
Enhanced FastAPI application for Aadhaar UID masking tool.
Provides endpoints for single and bulk image processing with database storage and encryption.
"""

import os
import sys
import uuid
import shutil
from pathlib import Path
from typing import List, Optional
from datetime import datetime
import logging

from fastapi import FastAPI, File, UploadFile, HTTPException, Request, Query, Depends
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from bson import ObjectId
import io

# Add src directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.ocr_detector import AadhaarOCRDetector
from src.image_masker import AadhaarImageMasker
from src.config import config
from src.database import db_manager
from src.encryption import encryption
from src.storage import secure_storage
from src.models import ProcessResult, StoredRecordResponse, RecordListResponse

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Enhanced Aadhaar UID Masking API",
    description="API for detecting and masking Aadhaar numbers in images with secure database storage",
    version="2.0.0"
)

@app.on_event("startup")
async def startup_event():
    """Initialize database connection on startup."""
    try:
        connected = await db_manager.connect()
        if connected:
            logger.info("Database connected successfully")
        else:
            logger.warning("Database connection failed, but API will continue without storage features")
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        logger.warning("API will start without database storage capabilities")
        # Don't fail startup - allow API to run without MongoDB

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up database connection on shutdown."""
    try:
        await db_manager.disconnect()
        logger.info("Database disconnected successfully")
    except Exception as e:
        logger.error(f"Error during database disconnect: {e}")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create directories
UPLOAD_DIR = Path("uploads")
OUTPUT_DIR = Path("output")
STATIC_DIR = Path("static")

for directory in [UPLOAD_DIR, OUTPUT_DIR, STATIC_DIR]:
    directory.mkdir(exist_ok=True)

# Mount static files to serve processed images
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Initialize detector and masker
detector = AadhaarOCRDetector(use_easyocr=True)
masker = AadhaarImageMasker()

class BulkProcessResult(BaseModel):
    """Response model for bulk processing results."""
    total_images: int
    successful_processes: int
    failed_processes: int
    results: List[ProcessResult]
    errors: List[str]

def save_uploaded_file(upload_file: UploadFile, destination: Path) -> None:
    """Save uploaded file to destination."""
    try:
        with destination.open("wb") as buffer:
            shutil.copyfileobj(upload_file.file, buffer)
    finally:
        upload_file.file.close()

def get_frontend_html() -> str:
    """Return the frontend HTML content from template file."""
    try:
        template_path = Path("templates/index.html")
        if template_path.exists():
            return template_path.read_text(encoding='utf-8')
        else:
            raise FileNotFoundError("Template file not found")
    except Exception as e:
        logger.warning(f"Could not load template file: {e}")
        # Fallback to basic HTML if template not found
        return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Aadhaar UID Masking Tool</title>
    <style>body { font-family: Arial, sans-serif; text-align: center; padding: 50px; }</style>
</head>
<body>
    <h1>Aadhaar UID Masking Tool</h1>
    <p>Template not found. Please ensure the template file exists at templates/index.html</p>
    <p>API endpoints are available at:</p>
    <ul style="list-style: none;">
        <li><a href="/api/info">/api/info</a> - API information</li>
        <li><a href="/health">/health</a> - Health check</li>
    </ul>
</body>
</html>"""


def process_single_image(image_path: str, output_filename: str, base_url: str) -> ProcessResult:
    """Process a single image and return results."""
    start_time = datetime.now()
    
    try:
        # Detect Aadhaar number with all locations
        detection_result = detector.detect_aadhaar_number_with_all_locations(image_path)
        
        if not detection_result:
            raise HTTPException(status_code=422, detail="No Aadhaar number detected in the image")
        
        aadhaar_number, bboxes = detection_result
        
        # Mask the Aadhaar number
        masked_number = masker.mask_aadhaar_number(aadhaar_number)
        
        # Create output path
        output_path = STATIC_DIR / output_filename
        
        # Apply masking
        if bboxes:
            # Use detected locations for precise replacement
            success = masker.replace_text_at_all_locations(
                image_path, aadhaar_number, masked_number, bboxes, str(output_path)
            )
        else:
            # Fallback to general replacement
            success = masker.replace_text_in_image(
                image_path, aadhaar_number, masked_number, str(output_path)
            )
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to create masked image")
        
        # Calculate processing time
        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds()
        
        # Create response
        result = ProcessResult(
            filename=Path(image_path).name,
            uid_numbers=[aadhaar_number],
            masked_image_url=f"{base_url}/static/{output_filename}",
            processing_time=processing_time,
            locations_found=len(bboxes) if bboxes else 0
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")

@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the frontend HTML application."""
    return get_frontend_html()

@app.get("/api/info")
async def api_info():
    """API information endpoint."""
    return {
        "message": "Aadhaar UID Masking API",
        "version": "1.0.0",
        "endpoints": {
            "single_image": "/process-image",
            "bulk_images": "/process-bulk",
            "health": "/health"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.post("/process-image", response_model=ProcessResult)
async def process_image(request: Request, file: UploadFile = File(...), store: bool = Query(False, description="Store processed image in database")):
    """
    Process a single image to detect and mask Aadhaar numbers.
    
    Args:
        file: Image file to process (JPEG, PNG, etc.)
        
    Returns:
        ProcessResult: Results including masked image URL and detected UIDs
    """
    
    # Validate file type
    if not file.content_type or not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="File must be an image")
    
    # Generate unique filename
    file_id = str(uuid.uuid4())
    original_filename = f"{file_id}_{file.filename}"
    masked_filename = f"{file_id}_masked_{file.filename}"
    
    # Save uploaded file
    upload_path = UPLOAD_DIR / original_filename
    save_uploaded_file(file, upload_path)
    
    try:
        # Get base URL for response
        base_url = str(request.base_url).rstrip('/')
        
        # Process the image
        result = process_single_image(str(upload_path), masked_filename, base_url)
        
        # Store in database if requested
        if store:
            try:
                processing_metadata = {
                    "processing_time": result.processing_time,
                    "locations_found": result.locations_found,
                    "uid_numbers_count": len(result.uid_numbers),
                    "file_size_original": upload_path.stat().st_size,
                    "file_size_masked": (STATIC_DIR / masked_filename).stat().st_size,
                    "image_format": file.content_type or "unknown"
                }
                
                # Store with encryption
                record_id = await secure_storage.store_processed_card(
                    original_image_path=str(upload_path),
                    masked_image_path=str(STATIC_DIR / masked_filename),
                    aadhaar_number=result.uid_numbers[0],  # First detected UID
                    filename=file.filename,
                    processing_metadata=processing_metadata
                )
                
                result.record_id = str(record_id)
                logger.info(f"Stored processed image in database: {record_id}")
                
            except Exception as e:
                logger.error(f"Failed to store in database: {e}")
                # Continue without storage - don't fail the entire request
        
        return result
        
    finally:
        # Clean up uploaded file
        if upload_path.exists():
            upload_path.unlink()

@app.post("/process-bulk", response_model=BulkProcessResult)
async def process_bulk_images(request: Request, files: List[UploadFile] = File(...)):
    """
    Process multiple images to detect and mask Aadhaar numbers.
    
    Args:
        files: List of image files to process
        
    Returns:
        BulkProcessResult: Results for all processed images
    """
    
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")
    
    if len(files) > 10:  # Limit bulk processing
        raise HTTPException(status_code=400, detail="Maximum 10 files allowed for bulk processing")
    
    results = []
    errors = []
    successful_processes = 0
    
    # Get base URL for response
    base_url = str(request.base_url).rstrip('/')
    
    for i, file in enumerate(files):
        try:
            # Validate file type
            if not file.content_type or not file.content_type.startswith('image/'):
                errors.append(f"File {i+1} ({file.filename}): Must be an image")
                continue
            
            # Generate unique filename
            file_id = str(uuid.uuid4())
            original_filename = f"{file_id}_{file.filename}"
            masked_filename = f"{file_id}_masked_{file.filename}"
            
            # Save uploaded file
            upload_path = UPLOAD_DIR / original_filename
            save_uploaded_file(file, upload_path)
            
            try:
                # Process the image
                result = process_single_image(str(upload_path), masked_filename, base_url)
                results.append(result)
                successful_processes += 1
                
            except HTTPException as e:
                errors.append(f"File {i+1} ({file.filename}): {e.detail}")
            except Exception as e:
                errors.append(f"File {i+1} ({file.filename}): Processing error - {str(e)}")
            finally:
                # Clean up uploaded file
                if upload_path.exists():
                    upload_path.unlink()
                
        except Exception as e:
            errors.append(f"File {i+1} ({file.filename}): Upload error - {str(e)}")
    
    # Create bulk response
    bulk_result = BulkProcessResult(
        total_images=len(files),
        successful_processes=successful_processes,
        failed_processes=len(files) - successful_processes,
        results=results,
        errors=errors
    )
    
    return bulk_result

@app.get("/download/{filename}")
async def download_file(filename: str):
    """
    Download a processed image file with proper headers for browser download.
    
    Args:
        filename: Name of the file to download
        
    Returns:
        FileResponse: The requested file with download headers
    """
    file_path = STATIC_DIR / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    # Determine media type based on file extension
    file_extension = file_path.suffix.lower()
    media_type_map = {
        '.png': 'image/png',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.gif': 'image/gif',
        '.bmp': 'image/bmp',
        '.webp': 'image/webp'
    }
    media_type = media_type_map.get(file_extension, 'application/octet-stream')
    
    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type=media_type,
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0"
        }
    )

@app.delete("/cleanup")
async def cleanup_files():
    """
    Clean up old processed files (admin endpoint).
    
    Returns:
        dict: Cleanup results
    """
    try:
        # Clean up files older than 1 hour
        import time
        current_time = time.time()
        deleted_count = 0
        
        for file_path in STATIC_DIR.iterdir():
            if file_path.is_file():
                file_age = current_time - file_path.stat().st_mtime
                if file_age > 3600:  # 1 hour
                    file_path.unlink()
                    deleted_count += 1
        
        return {
            "message": f"Cleanup completed. {deleted_count} files deleted.",
            "deleted_count": deleted_count
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cleanup error: {str(e)}")

# New Database Storage Endpoints

@app.post("/process-and-store-image", response_model=ProcessResult)
async def process_and_store_image(request: Request, file: UploadFile = File(...)):
    """
    Process a single image and automatically store in database with encryption.
    """
    # Validate file type
    if not file.content_type or not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="File must be an image")
    
    # Generate unique filename
    file_id = str(uuid.uuid4())
    original_filename = f"{file_id}_{file.filename}"
    masked_filename = f"{file_id}_masked_{file.filename}"
    
    # Save uploaded file
    upload_path = UPLOAD_DIR / original_filename
    save_uploaded_file(file, upload_path)
    
    try:
        # Get base URL for response
        base_url = str(request.base_url).rstrip('/')
        
        # Process the image
        result = process_single_image(str(upload_path), masked_filename, base_url)
        
        # Store in database with encryption
        processing_metadata = {
            "processing_time": result.processing_time,
            "locations_found": result.locations_found,
            "uid_numbers_count": len(result.uid_numbers),
            "file_size_original": upload_path.stat().st_size,
            "file_size_masked": (STATIC_DIR / masked_filename).stat().st_size,
            "image_format": file.content_type or "unknown"
        }
        
        record_id = await secure_storage.store_processed_card(
            original_image_path=str(upload_path),
            masked_image_path=str(STATIC_DIR / masked_filename),
            aadhaar_number=result.uid_numbers[0],
            filename=file.filename,
            processing_metadata=processing_metadata
        )
        
        result.record_id = str(record_id)
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing and storage error: {str(e)}")
    finally:
        # Clean up uploaded file
        if upload_path.exists():
            upload_path.unlink()

@app.get("/retrieve-image/{record_id}/{image_type}")
async def retrieve_image(record_id: str, image_type: str):
    """
    Retrieve a decrypted image from database storage.
    
    Args:
        record_id: Database record ID
        image_type: 'original' or 'masked'
    """
    try:
        # Validate image_type
        if image_type not in ['original', 'masked']:
            raise HTTPException(status_code=400, detail="image_type must be 'original' or 'masked'")
        
        # Convert record_id to ObjectId
        try:
            object_id = ObjectId(record_id)
        except:
            raise HTTPException(status_code=400, detail="Invalid record ID format")
        
        # Retrieve image
        image_data, content_type, filename = await secure_storage.retrieve_encrypted_image(
            object_id, image_type
        )
        
        if image_data is None:
            raise HTTPException(status_code=404, detail="Image not found")
        
        # Return as streaming response
        return StreamingResponse(
            io.BytesIO(image_data),
            media_type=content_type,
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Image retrieval error: {str(e)}")

@app.get("/get-record/{record_id}", response_model=StoredRecordResponse)
async def get_record(record_id: str, request: Request):
    """
    Get record metadata with decrypted UID (masked for display).
    """
    try:
        # Convert record_id to ObjectId
        try:
            object_id = ObjectId(record_id)
        except:
            raise HTTPException(status_code=400, detail="Invalid record ID format")
        
        # Retrieve record
        record = await secure_storage.retrieve_record_with_decrypted_uid(object_id)
        
        if not record:
            raise HTTPException(status_code=404, detail="Record not found")
        
        # Get base URL
        base_url = str(request.base_url).rstrip('/')
        
        # Create response
        response = StoredRecordResponse(
            id=str(record["_id"]),
            filename=record["filename"],
            uid_numbers=record["uid_numbers"],
            created_at=record["created_at"],
            status=record["status"],
            original_image_url=f"{base_url}/retrieve-image/{record_id}/original",
            masked_image_url=f"{base_url}/retrieve-image/{record_id}/masked"
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Record retrieval error: {str(e)}")

@app.get("/list-records", response_model=RecordListResponse)
async def list_records(
    request: Request,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Records per page"),
    search: Optional[str] = Query(None, description="Search term for filename")
):
    """
    List stored records with pagination and optional search.
    """
    try:
        # Calculate skip
        skip = (page - 1) * page_size
        
        # Get records
        if search:
            records, total_count = await secure_storage.search_records_by_filename(
                search, skip, page_size
            )
        else:
            records, total_count = await secure_storage.list_stored_records(
                skip, page_size
            )
        
        # Get base URL
        base_url = str(request.base_url).rstrip('/')
        
        # Convert to response format
        record_responses = []
        for record in records:
            record_id = str(record["_id"])
            record_response = StoredRecordResponse(
                id=record_id,
                filename=record["filename"],
                uid_numbers=record.get("uid_numbers", ["XXXX XXXX XXXX"]),
                created_at=record["created_at"],
                status=record["status"],
                original_image_url=f"{base_url}/retrieve-image/{record_id}/original",
                masked_image_url=f"{base_url}/retrieve-image/{record_id}/masked"
            )
            record_responses.append(record_response)
        
        # Calculate total pages
        total_pages = (total_count + page_size - 1) // page_size
        
        return RecordListResponse(
            records=record_responses,
            total_count=total_count,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Record listing error: {str(e)}")

@app.delete("/delete-record/{record_id}")
async def delete_record(record_id: str):
    """
    Delete a stored record and its associated encrypted files.
    """
    try:
        # Convert record_id to ObjectId
        try:
            object_id = ObjectId(record_id)
        except:
            raise HTTPException(status_code=400, detail="Invalid record ID format")
        
        # Delete record
        success = await secure_storage.delete_stored_record(object_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Record not found or deletion failed")
        
        return {"message": f"Record {record_id} deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Record deletion error: {str(e)}")

@app.get("/statistics")
async def get_statistics():
    """
    Get system statistics including database and encryption info.
    """
    try:
        stats = await secure_storage.get_storage_statistics()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Statistics error: {str(e)}")

@app.get("/health")
async def enhanced_health_check():
    """Enhanced health check including database and encryption status."""
    try:
        # Check database connectivity
        db_connected = db_manager._connection_validated
        
        # Check encryption system
        encryption_ready = True
        try:
            encryption.get_encryption_info()
        except:
            encryption_ready = False
        
        return {
            "status": "healthy" if db_connected and encryption_ready else "degraded",
            "timestamp": datetime.now().isoformat(),
            "database_connected": db_connected,
            "encryption_ready": encryption_ready,
            "version": "2.0.0"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "timestamp": datetime.now().isoformat(),
            "error": str(e),
            "version": "2.0.0"
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=config.API_HOST, port=config.API_PORT) 
