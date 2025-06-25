# Aadhaar UID Masking API

A FastAPI-based web service for detecting and masking Aadhaar numbers in images.

## Features

- **Single Image Processing**: Process one image at a time
- **Bulk Image Processing**: Process up to 10 images simultaneously
- **Automatic UID Detection**: Uses OCR to detect Aadhaar numbers
- **Smart Masking**: Masks first 8 digits while preserving document layout
- **File Management**: Automatic cleanup of processed files

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Start the server:
```bash
python run_api.py
```

The API will be available at `http://localhost:8000`

## API Endpoints

### 1. Single Image Processing

**Endpoint**: `POST /process-image`

**Description**: Process a single image to detect and mask Aadhaar numbers.

**Request**:
- Method: POST
- Content-Type: multipart/form-data
- Body: File upload (image file)

**Response**:
```json
{
  "filename": "example.jpg",
  "uid_numbers": ["XXXX XXXX 9012"],
  "masked_image_url": "http://localhost:8000/static/masked_example.jpg",
  "processing_time": 2.5,
  "locations_found": 2
}
```

**cURL Example**:
```bash
curl -X POST "http://localhost:8000/process-image" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@aadhaar_image.jpg"
```

### 2. Bulk Image Processing

**Endpoint**: `POST /process-bulk`

**Description**: Process multiple images (up to 10) simultaneously.

**Request**:
- Method: POST
- Content-Type: multipart/form-data
- Body: Multiple file uploads

**Response**:
```json
{
  "total_images": 3,
  "successful_processes": 2,
  "failed_processes": 1,
  "results": [
    {
      "filename": "image1.jpg",
      "uid_numbers": ["XXXX XXXX 9012"],
      "masked_image_url": "http://localhost:8000/static/masked_image1.jpg",
      "processing_time": 2.1,
      "locations_found": 1
    }
  ],
  "errors": [
    "File 3 (invalid.txt): Must be an image"
  ]
}
```

**cURL Example**:
```bash
curl -X POST "http://localhost:8000/process-bulk" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "files=@image1.jpg" \
  -F "files=@image2.jpg" \
  -F "files=@image3.jpg"
```

### 3. Health Check

**Endpoint**: `GET /health`

**Description**: Check if the API is running.

**Response**:
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00"
}
```

### 4. Download Processed Image

**Endpoint**: `GET /download/{filename}`

**Description**: Download a processed image file.

**Example**:
```bash
curl -O "http://localhost:8000/download/masked_example.jpg"
```

### 5. File Cleanup (Admin)

**Endpoint**: `DELETE /cleanup`

**Description**: Clean up old processed files (files older than 1 hour).

**Response**:
```json
{
  "message": "Cleanup completed. 5 files deleted.",
  "deleted_count": 5
}
```

## Response Models

### ProcessResult
- `filename`: Original filename
- `uid_numbers`: List of detected Aadhaar numbers (masked)
- `masked_image_url`: URL to access the masked image
- `processing_time`: Time taken to process (seconds)
- `locations_found`: Number of locations where UID was found

### BulkProcessResult
- `total_images`: Total number of images submitted
- `successful_processes`: Number of successfully processed images
- `failed_processes`: Number of failed processes
- `results`: List of ProcessResult objects
- `errors`: List of error messages for failed processes

## Error Handling

The API returns appropriate HTTP status codes:

- `200`: Success
- `400`: Bad Request (invalid file type, too many files)
- `404`: File not found
- `422`: Unprocessable Entity (no Aadhaar number detected)
- `500`: Internal Server Error

## File Management

- **Uploads**: Temporary files are automatically deleted after processing
- **Static Files**: Processed images are served from `/static/` endpoint
- **Cleanup**: Files older than 1 hour can be cleaned up using the `/cleanup` endpoint

## Interactive Documentation

FastAPI provides automatic interactive API documentation:

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

## Environment Variables

You can configure the server using environment variables:

- `HOST`: Server host (default: 0.0.0.0)
- `PORT`: Server port (default: 8000)
- `RELOAD`: Enable auto-reload during development (default: True)

## Example Usage with Python Requests

```python
import requests

# Single image processing
with open('aadhaar_card.jpg', 'rb') as f:
    files = {'file': f}
    response = requests.post('http://localhost:8000/process-image', files=files)
    result = response.json()
    print(f"Masked image URL: {result['masked_image_url']}")

# Bulk processing
files = [
    ('files', open('image1.jpg', 'rb')),
    ('files', open('image2.jpg', 'rb')),
    ('files', open('image3.jpg', 'rb'))
]
response = requests.post('http://localhost:8000/process-bulk', files=files)
result = response.json()
print(f"Successfully processed: {result['successful_processes']} images")
```

## Notes

- Maximum file size is handled by FastAPI defaults
- Supported image formats: JPEG, PNG, and other common formats
- The API masks only the first 8 digits of Aadhaar numbers
- Processing time varies based on image size and complexity
- Bulk processing is limited to 10 images per request 