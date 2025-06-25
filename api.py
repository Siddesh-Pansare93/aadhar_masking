#!/usr/bin/env python3
"""
FastAPI application for Aadhaar UID masking tool.
Provides endpoints for single and bulk image processing.
"""

import os
import sys
import uuid
import shutil
from pathlib import Path
from typing import List, Optional
from datetime import datetime

from fastapi import FastAPI, File, UploadFile, HTTPException, Request
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Add src directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.ocr_detector import AadhaarOCRDetector
from src.image_masker import AadhaarImageMasker

# Create FastAPI app
app = FastAPI(
    title="Aadhaar UID Masking API",
    description="API for detecting and masking Aadhaar numbers in images",
    version="1.0.0"
)

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

class ProcessResult(BaseModel):
    """Response model for image processing results."""
    filename: str
    uid_numbers: List[str]
    masked_image_url: str
    processing_time: float
    locations_found: int

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
    """Return the frontend HTML content."""
    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Aadhaar UID Masking Tool</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
            overflow: hidden;
        }

        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            text-align: center;
            padding: 40px 20px;
        }

        .header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
            font-weight: 300;
        }

        .header p {
            font-size: 1.1em;
            opacity: 0.9;
        }

        .main-content {
            padding: 40px;
        }

        .tabs {
            display: flex;
            justify-content: center;
            margin-bottom: 40px;
            border-bottom: 1px solid #eee;
        }

        .tab {
            padding: 15px 30px;
            cursor: pointer;
            border: none;
            background: none;
            font-size: 1.1em;
            color: #666;
            border-bottom: 3px solid transparent;
            transition: all 0.3s ease;
        }

        .tab.active {
            color: #667eea;
            border-bottom-color: #667eea;
        }

        .tab:hover {
            color: #667eea;
        }

        .tab-content {
            display: none;
        }

        .tab-content.active {
            display: block;
        }

        .upload-area {
            border: 3px dashed #ddd;
            border-radius: 15px;
            padding: 40px;
            text-align: center;
            margin-bottom: 30px;
            transition: all 0.3s ease;
            cursor: pointer;
        }

        .upload-area.dragover {
            border-color: #667eea;
            background-color: #f8f9ff;
        }

        .upload-area:hover {
            border-color: #667eea;
            background-color: #f8f9ff;
        }

        .upload-icon {
            font-size: 3em;
            color: #ddd;
            margin-bottom: 20px;
        }

        .upload-text {
            font-size: 1.2em;
            color: #666;
            margin-bottom: 10px;
        }

        .upload-subtext {
            color: #999;
            font-size: 0.9em;
        }

        .file-input {
            display: none;
        }

        .btn {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 15px 30px;
            border-radius: 50px;
            font-size: 1.1em;
            cursor: pointer;
            transition: all 0.3s ease;
            margin: 10px;
            min-width: 150px;
        }

        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 20px rgba(102, 126, 234, 0.3);
        }

        .btn:disabled {
            background: #ccc;
            cursor: not-allowed;
            transform: none;
            box-shadow: none;
        }

        .processing {
            display: none;
            text-align: center;
            padding: 20px;
        }

        .processing.show {
            display: block;
        }

        .spinner {
            width: 40px;
            height: 40px;
            border: 4px solid #f3f3f3;
            border-top: 4px solid #667eea;
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin: 0 auto 20px;
        }

        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }

        .results {
            margin-top: 30px;
        }

        .result-card {
            background: #f8f9fa;
            border-radius: 15px;
            padding: 25px;
            margin-bottom: 20px;
            border-left: 5px solid #667eea;
            box-shadow: 0 5px 15px rgba(0, 0, 0, 0.05);
        }

        .result-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
        }

        .result-filename {
            font-weight: bold;
            color: #333;
            font-size: 1.1em;
        }

        .result-status {
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 0.9em;
            font-weight: bold;
        }

        .status-success {
            background: #d4edda;
            color: #155724;
        }

        .status-error {
            background: #f8d7da;
            color: #721c24;
        }

        .result-details {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 20px;
        }

        .detail-item {
            background: white;
            padding: 15px;
            border-radius: 10px;
            text-align: center;
        }

        .detail-label {
            font-size: 0.9em;
            color: #666;
            margin-bottom: 5px;
        }

        .detail-value {
            font-size: 1.1em;
            font-weight: bold;
            color: #333;
        }

        .uid-number {
            font-family: 'Courier New', monospace;
            background: #e9ecef;
            padding: 5px 10px;
            border-radius: 5px;
            display: inline-block;
            margin: 2px;
        }

        .image-container {
            text-align: center;
            margin-top: 20px;
        }

        .masked-image {
            max-width: 100%;
            max-height: 400px;
            border-radius: 10px;
            box-shadow: 0 10px 25px rgba(0, 0, 0, 0.1);
            margin: 10px 0;
        }

        .download-btn {
            background: #28a745;
            margin-top: 10px;
        }

        .download-btn:hover {
            background: #218838;
        }

        .file-list {
            margin-top: 20px;
        }

        .file-item {
            background: #f8f9fa;
            padding: 15px;
            border-radius: 10px;
            margin-bottom: 10px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .file-name {
            font-weight: bold;
        }

        .file-size {
            color: #666;
            font-size: 0.9em;
        }

        .remove-file {
            background: #dc3545;
            color: white;
            border: none;
            padding: 5px 10px;
            border-radius: 5px;
            cursor: pointer;
            font-size: 0.8em;
        }

        .error-message {
            background: #f8d7da;
            color: #721c24;
            padding: 15px;
            border-radius: 10px;
            margin: 10px 0;
            border-left: 5px solid #dc3545;
        }

        .summary-stats {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 15px;
            margin-bottom: 20px;
            text-align: center;
        }

        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 20px;
            margin-top: 15px;
        }

        .stat-item {
            text-align: center;
        }

        .stat-number {
            font-size: 2em;
            font-weight: bold;
            margin-bottom: 5px;
        }

        .stat-label {
            font-size: 0.9em;
            opacity: 0.9;
        }

        @media (max-width: 768px) {
            .header h1 {
                font-size: 2em;
            }

            .main-content {
                padding: 20px;
            }

            .tabs {
                flex-direction: column;
            }

            .tab {
                border-bottom: none;
                border-right: 3px solid transparent;
            }

            .tab.active {
                border-right-color: #667eea;
                border-bottom-color: transparent;
            }

            .result-details {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔐 Aadhaar UID Masking Tool</h1>
            <p>Securely detect and mask Aadhaar numbers in your documents</p>
        </div>

        <div class="main-content">
            <div class="tabs">
                <button class="tab active" onclick="switchTab('single')">
                    📄 Single Image
                </button>
                <button class="tab" onclick="switchTab('bulk')">
                    📚 Bulk Processing
                </button>
            </div>

            <!-- Single Image Tab -->
            <div id="single-tab" class="tab-content active">
                <div class="upload-area" onclick="document.getElementById('single-file').click()">
                    <div class="upload-icon">📸</div>
                    <div class="upload-text">Click to select an image</div>
                    <div class="upload-subtext">or drag and drop your Aadhaar card image here</div>
                </div>
                <input type="file" id="single-file" class="file-input" accept="image/*">
                
                <div style="text-align: center;">
                    <button class="btn" onclick="processSingleImage()" id="single-process-btn" disabled>
                        Process Image
                    </button>
                </div>

                <div id="single-processing" class="processing">
                    <div class="spinner"></div>
                    <p>Processing your image...</p>
                </div>

                <div id="single-results" class="results"></div>
            </div>

            <!-- Bulk Processing Tab -->
            <div id="bulk-tab" class="tab-content">
                <div class="upload-area" onclick="document.getElementById('bulk-files').click()">
                    <div class="upload-icon">📚</div>
                    <div class="upload-text">Click to select multiple images</div>
                    <div class="upload-subtext">or drag and drop up to 10 images here</div>
                </div>
                <input type="file" id="bulk-files" class="file-input" accept="image/*" multiple>
                
                <div id="bulk-file-list" class="file-list"></div>

                <div style="text-align: center;">
                    <button class="btn" onclick="processBulkImages()" id="bulk-process-btn" disabled>
                        Process All Images
                    </button>
                    <button class="btn" onclick="clearBulkFiles()" style="background: #6c757d;">
                        Clear All
                    </button>
                </div>

                <div id="bulk-processing" class="processing">
                    <div class="spinner"></div>
                    <p>Processing your images...</p>
                </div>

                <div id="bulk-results" class="results"></div>
            </div>
        </div>
    </div>

    <script>
        // Use relative URLs since we're hosted from the same server
        const API_BASE_URL = window.location.origin;
        let selectedFiles = [];

        // Tab switching
        function switchTab(tabName) {
            // Update tab buttons
            document.querySelectorAll('.tab').forEach(tab => tab.classList.remove('active'));
            event.target.classList.add('active');

            // Update tab content
            document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));
            document.getElementById(`${tabName}-tab`).classList.add('active');

            // Clear results when switching tabs
            document.getElementById('single-results').innerHTML = '';
            document.getElementById('bulk-results').innerHTML = '';
        }

        // File handling for single image
        document.getElementById('single-file').addEventListener('change', function(e) {
            const file = e.target.files[0];
            const processBtn = document.getElementById('single-process-btn');
            
            if (file) {
                processBtn.disabled = false;
                processBtn.textContent = `Process "${file.name}"`;
            } else {
                processBtn.disabled = true;
                processBtn.textContent = 'Process Image';
            }
        });

        // File handling for bulk images
        document.getElementById('bulk-files').addEventListener('change', function(e) {
            const files = Array.from(e.target.files);
            addBulkFiles(files);
        });

        function addBulkFiles(files) {
            files.forEach(file => {
                if (selectedFiles.length < 10 && !selectedFiles.find(f => f.name === file.name)) {
                    selectedFiles.push(file);
                }
            });
            updateBulkFileList();
        }

        function updateBulkFileList() {
            const fileList = document.getElementById('bulk-file-list');
            const processBtn = document.getElementById('bulk-process-btn');
            
            if (selectedFiles.length === 0) {
                fileList.innerHTML = '';
                processBtn.disabled = true;
                processBtn.textContent = 'Process All Images';
                return;
            }

            processBtn.disabled = false;
            processBtn.textContent = `Process ${selectedFiles.length} Image${selectedFiles.length > 1 ? 's' : ''}`;

            fileList.innerHTML = selectedFiles.map((file, index) => `
                <div class="file-item">
                    <div>
                        <div class="file-name">${file.name}</div>
                        <div class="file-size">${formatFileSize(file.size)}</div>
                    </div>
                    <button class="remove-file" onclick="removeFile(${index})">Remove</button>
                </div>
            `).join('');
        }

        function removeFile(index) {
            selectedFiles.splice(index, 1);
            updateBulkFileList();
        }

        function clearBulkFiles() {
            selectedFiles = [];
            document.getElementById('bulk-files').value = '';
            updateBulkFileList();
        }

        function formatFileSize(bytes) {
            if (bytes === 0) return '0 Bytes';
            const k = 1024;
            const sizes = ['Bytes', 'KB', 'MB', 'GB'];
            const i = Math.floor(Math.log(bytes) / Math.log(k));
            return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
        }

        // Drag and drop functionality
        function setupDragAndDrop() {
            const uploadAreas = document.querySelectorAll('.upload-area');
            
            uploadAreas.forEach(area => {
                area.addEventListener('dragover', function(e) {
                    e.preventDefault();
                    this.classList.add('dragover');
                });

                area.addEventListener('dragleave', function(e) {
                    e.preventDefault();
                    this.classList.remove('dragover');
                });

                area.addEventListener('drop', function(e) {
                    e.preventDefault();
                    this.classList.remove('dragover');
                    
                    const files = Array.from(e.dataTransfer.files);
                    const isImages = files.every(file => file.type.startsWith('image/'));
                    
                    if (!isImages) {
                        alert('Please drop only image files.');
                        return;
                    }

                    if (this.closest('#single-tab')) {
                        if (files.length === 1) {
                            document.getElementById('single-file').files = e.dataTransfer.files;
                            document.getElementById('single-file').dispatchEvent(new Event('change'));
                        } else {
                            alert('Please drop only one image for single processing.');
                        }
                    } else if (this.closest('#bulk-tab')) {
                        addBulkFiles(files);
                    }
                });
            });
        }

        // Processing functions
        async function processSingleImage() {
            const fileInput = document.getElementById('single-file');
            const file = fileInput.files[0];
            
            if (!file) {
                alert('Please select an image file');
                return;
            }

            showProcessing('single');
            
            try {
                const formData = new FormData();
                formData.append('file', file);

                const response = await fetch(`${API_BASE_URL}/process-image`, {
                    method: 'POST',
                    body: formData
                });

                if (response.ok) {
                    const result = await response.json();
                    displaySingleResult(result);
                } else {
                    const errorData = await response.json();
                    throw new Error(errorData.detail || `HTTP ${response.status}`);
                }
            } catch (error) {
                displayError('single-results', error.message);
            } finally {
                hideProcessing('single');
            }
        }

        async function processBulkImages() {
            if (selectedFiles.length === 0) {
                alert('Please select image files');
                return;
            }

            showProcessing('bulk');

            try {
                const formData = new FormData();
                selectedFiles.forEach(file => {
                    formData.append('files', file);
                });

                const response = await fetch(`${API_BASE_URL}/process-bulk`, {
                    method: 'POST',
                    body: formData
                });

                if (response.ok) {
                    const result = await response.json();
                    displayBulkResults(result);
                } else {
                    const errorData = await response.json();
                    throw new Error(errorData.detail || `HTTP ${response.status}`);
                }
            } catch (error) {
                displayError('bulk-results', error.message);
            } finally {
                hideProcessing('bulk');
            }
        }

        function showProcessing(type) {
            document.getElementById(`${type}-processing`).classList.add('show');
            document.getElementById(`${type}-results`).innerHTML = '';
        }

        function hideProcessing(type) {
            document.getElementById(`${type}-processing`).classList.remove('show');
        }

        function displaySingleResult(result) {
            const resultsDiv = document.getElementById('single-results');
            
            resultsDiv.innerHTML = `
                <div class="result-card">
                    <div class="result-header">
                        <div class="result-filename">${result.filename}</div>
                        <div class="result-status status-success">✓ Success</div>
                    </div>
                    
                    <div class="result-details">
                        <div class="detail-item">
                            <div class="detail-label">Processing Time</div>
                            <div class="detail-value">${result.processing_time.toFixed(2)}s</div>
                        </div>
                        <div class="detail-item">
                            <div class="detail-label">Locations Found</div>
                            <div class="detail-value">${result.locations_found}</div>
                        </div>
                        <div class="detail-item">
                            <div class="detail-label">UID Numbers</div>
                            <div class="detail-value">
                                ${result.uid_numbers.map(uid => `<span class="uid-number">${uid}</span>`).join('')}
                            </div>
                        </div>
                    </div>

                    <div class="image-container">
                        <h4>Masked Image:</h4>
                        <img src="${result.masked_image_url}" alt="Masked Image" class="masked-image" 
                             onerror="this.style.display='none'; this.nextElementSibling.style.display='block';">
                        <div style="display:none; color: #dc3545; padding: 20px;">Failed to load image</div>
                        <br>
                        <button class="btn download-btn" onclick="downloadImage('${result.masked_image_url}', '${result.filename}')">
                            📥 Download Masked Image
                        </button>
                    </div>
                </div>
            `;
        }

        function displayBulkResults(results) {
            const resultsDiv = document.getElementById('bulk-results');
            
            let html = `
                <div class="summary-stats">
                    <h3>Processing Summary</h3>
                    <div class="stats-grid">
                        <div class="stat-item">
                            <div class="stat-number">${results.total_images}</div>
                            <div class="stat-label">Total Images</div>
                        </div>
                        <div class="stat-item">
                            <div class="stat-number">${results.successful_processes}</div>
                            <div class="stat-label">Successful</div>
                        </div>
                        <div class="stat-item">
                            <div class="stat-number">${results.failed_processes}</div>
                            <div class="stat-label">Failed</div>
                        </div>
                    </div>
                </div>
            `;

            // Display errors if any
            if (results.errors && results.errors.length > 0) {
                html += `<div class="error-message">
                    <h4>❌ Errors:</h4>
                    ${results.errors.map(error => `<div>• ${error}</div>`).join('')}
                </div>`;
            }

            // Display successful results
            results.results.forEach(result => {
                html += `
                    <div class="result-card">
                        <div class="result-header">
                            <div class="result-filename">${result.filename}</div>
                            <div class="result-status status-success">✓ Success</div>
                        </div>
                        
                        <div class="result-details">
                            <div class="detail-item">
                                <div class="detail-label">Processing Time</div>
                                <div class="detail-value">${result.processing_time.toFixed(2)}s</div>
                            </div>
                            <div class="detail-item">
                                <div class="detail-label">Locations Found</div>
                                <div class="detail-value">${result.locations_found}</div>
                            </div>
                            <div class="detail-item">
                                <div class="detail-label">UID Numbers</div>
                                <div class="detail-value">
                                    ${result.uid_numbers.map(uid => `<span class="uid-number">${uid}</span>`).join('')}
                                </div>
                            </div>
                        </div>

                        <div class="image-container">
                            <h4>Masked Image:</h4>
                            <img src="${result.masked_image_url}" alt="Masked Image" class="masked-image"
                                 onerror="this.style.display='none'; this.nextElementSibling.style.display='block';">
                            <div style="display:none; color: #dc3545; padding: 20px;">Failed to load image</div>
                            <br>
                            <button class="btn download-btn" onclick="downloadImage('${result.masked_image_url}', '${result.filename}')">
                                📥 Download Masked Image
                            </button>
                        </div>
                    </div>
                `;
            });

            resultsDiv.innerHTML = html;
        }

        function displayError(containerId, errorMessage) {
            const container = document.getElementById(containerId);
            container.innerHTML = `
                <div class="error-message">
                    <h4>❌ Error</h4>
                    <p>${errorMessage}</p>
                </div>
            `;
        }

        function downloadImage(imageUrl, filename) {
            const link = document.createElement('a');
            link.href = imageUrl;
            link.download = `masked_${filename}`;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        }

        // Initialize drag and drop
        setupDragAndDrop();

        // Log API responses for debugging
        window.addEventListener('load', () => {
            console.log('Frontend loaded and ready!');
            console.log('API Base URL:', API_BASE_URL);
        });
    </script>
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
async def process_image(request: Request, file: UploadFile = File(...)):
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
    Download a processed image file.
    
    Args:
        filename: Name of the file to download
        
    Returns:
        FileResponse: The requested file
    """
    file_path = STATIC_DIR / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type='application/octet-stream'
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 