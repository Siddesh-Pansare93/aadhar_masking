# 🚀 Quick Start Guide

## One-Step Launch

### 1. Install Dependencies
```bash
cd siddesh
pip install -r requirements.txt
```

### 2. Start the Application
```bash
python run_api.py
```

### 3. Open in Browser
Navigate to: **http://localhost:8000**

That's it! 🎉

## What You Get

✅ **Complete Web Application** - Frontend + Backend in one server  
✅ **Beautiful UI** - Modern, responsive design  
✅ **Single Image Processing** - Upload one image at a time  
✅ **Bulk Processing** - Upload up to 10 images simultaneously  
✅ **Live Image Preview** - See masked results immediately  
✅ **Download Functionality** - Get your processed images  
✅ **API Documentation** - Available at `/docs`  

## Features

### 🖼️ Image Processing
- **Drag & Drop** or click to upload images
- **Real-time processing** with loading indicators
- **Automatic UID detection** using OCR
- **Smart masking** of first 8 digits
- **Multiple location detection** in same image

### 📊 Results Display
- **Processing statistics** (time, locations found)
- **UID numbers** detected and masked
- **Live image preview** of masked results
- **Individual download** buttons for each image
- **Error handling** with clear messages

### 🎨 Modern UI
- **Gradient design** with beautiful styling
- **Responsive layout** for mobile and desktop
- **Smooth animations** and hover effects
- **Tab-based interface** for easy navigation

## Endpoints

- **`/`** - Frontend Application (HTML UI)
- **`/process-image`** - Single image processing API
- **`/process-bulk`** - Bulk image processing API
- **`/static/{filename}`** - Static file serving (processed images)
- **`/docs`** - Interactive API documentation
- **`/api/info`** - API information

## Configuration

You can customize the server using environment variables:

```bash
# Custom host and port
HOST=0.0.0.0 PORT=9000 python run_api.py

# Disable auto-reload
RELOAD=false python run_api.py
```

## API Response Format

### Single Image Response:
```json
{
  "filename": "aadhaar_card.jpg",
  "uid_numbers": ["XXXX XXXX 9012"],
  "masked_image_url": "http://localhost:8000/static/masked_image.jpg",
  "processing_time": 2.5,
  "locations_found": 2
}
```

### Bulk Processing Response:
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

## Troubleshooting

**Frontend not loading?**
- Ensure you're visiting `http://localhost:8000` (not just localhost)
- Check if the server started successfully

**Images not displaying?**
- Verify the API server is running
- Check browser console for errors

**Processing errors?**
- Ensure uploaded files are valid images
- Check if Aadhaar numbers are clearly visible in the image

**API not responding?**
- Confirm all dependencies are installed: `pip install -r requirements.txt`
- Check if port 8000 is available

## File Structure

```
siddesh/
├── api.py              # Main FastAPI application (includes frontend)
├── run_api.py          # Server startup script
├── requirements.txt    # Python dependencies
├── src/
│   ├── ocr_detector.py # OCR and UID detection
│   └── image_masker.py # Image masking functionality
├── uploads/            # Temporary upload storage (auto-created)
├── static/             # Processed images storage (auto-created)
└── output/             # Additional output storage (auto-created)
```

## Development

For development with auto-reload:
```bash
python run_api.py  # Auto-reload enabled by default
```

For production:
```bash
RELOAD=false python run_api.py
```

## Next Steps

1. **Upload test images** with Aadhaar cards
2. **Try both single and bulk** processing
3. **Download masked images** to verify results
4. **Explore API documentation** at `/docs`
5. **Integrate with your applications** using the API endpoints 