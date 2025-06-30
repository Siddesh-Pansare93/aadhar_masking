#!/usr/bin/env python3
"""
Enhanced FastAPI application for Aadhaar UID masking tool.
Provides endpoints for single and bulk image processing with database storage and encryption.
Includes API key authentication and admin management.
"""

import os
import sys
import uuid
import shutil
from pathlib import Path
from typing import List, Optional
from datetime import datetime, timedelta
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
from src.models import (
    ProcessResult, StoredRecordResponse, RecordListResponse,
    APIKeyCreate, APIKeyResponse, APIKeyListResponse, APIKeyAnalytics
)
from src.api_key_manager import api_key_manager
from src.auth import authenticate_api_key, authenticate_admin, log_api_request

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Enhanced Aadhaar UID Masking API with Authentication",
    description="API for detecting and masking Aadhaar numbers in images with secure database storage and API key authentication",
    version="3.0.0"
)

@app.on_event("startup")
async def startup_event():
    """Initialize database connection on startup."""
    try:
        connected = await db_manager.connect()
        if connected:
            logger.info("Database connected successfully")
            # Create indexes for new collections
            await create_indexes()
        else:
            logger.warning("Database connection failed, but API will continue without storage features")
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        logger.warning("API will start without database storage capabilities")

async def create_indexes():
    """Create database indexes for optimal performance."""
    try:
        # Indexes for API keys collection
        await db_manager.db.api_keys.create_index([("key_hash", 1)], unique=True)
        await db_manager.db.api_keys.create_index([("consumer_email", 1)])
        await db_manager.db.api_keys.create_index([("is_active", 1)])
        await db_manager.db.api_keys.create_index([("created_at", -1)])
        
        # Indexes for request logs collection
        await db_manager.db.request_logs.create_index([("api_key_id", 1)])
        await db_manager.db.request_logs.create_index([("timestamp", -1)])
        await db_manager.db.request_logs.create_index([("status", 1)])
        
        # Compound indexes
        await db_manager.db.request_logs.create_index([("api_key_id", 1), ("timestamp", -1)])
        
        logger.info("Database indexes created successfully")
        
    except Exception as e:
        logger.warning(f"Could not create all indexes: {e}")

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
    <title>Aadhaar UID Masking Tool with API Key Authentication</title>
    <style>body { font-family: Arial, sans-serif; text-align: center; padding: 50px; }</style>
</head>
<body>
    <h1>Aadhaar UID Masking Tool with API Key Authentication</h1>
    <p>This API requires authentication. Please contact the administrator for an API key.</p>
    <p>API endpoints are available at:</p>
    <ul style="list-style: none;">
        <li><a href="/api/info">/api/info</a> - API information</li>
        <li><a href="/health">/health</a> - Health check</li>
        <li><a href="/admin/dashboard">/admin/dashboard</a> - Admin dashboard (requires admin credentials)</li>
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

# ==== Public Endpoints (No Authentication Required) ====

@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the frontend HTML application."""
    return get_frontend_html()

@app.get("/api/info")
async def api_info():
    """API information endpoint."""
    return {
        "message": "Aadhaar UID Masking API with Authentication",
        "version": "3.0.0",
        "authentication": "API Key required (X-API-Key header)",
        "endpoints": {
            "single_image": "/process-image",
            "bulk_images": "/process-bulk",
            "admin_dashboard": "/admin/dashboard",
            "health": "/health"
        },
        "admin_contact": "Contact administrator for API key"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint."""
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
            "version": "3.0.0"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "timestamp": datetime.now().isoformat(),
            "error": str(e),
            "version": "3.0.0"
        }

# ==== Admin Endpoints (Basic Auth Required) ====

@app.get("/admin/dashboard", response_class=HTMLResponse)
async def admin_dashboard(admin_auth: bool = Depends(authenticate_admin)):
    """Admin dashboard HTML page."""
    return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Admin Dashboard - Aadhaar UID Masking</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .header { text-align: center; color: #333; margin-bottom: 30px; }
        .nav { display: flex; gap: 10px; margin-bottom: 20px; flex-wrap: wrap; }
        .nav button { padding: 10px 20px; background: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer; }
        .nav button:hover { background: #0056b3; }
        .section { display: none; margin-top: 20px; }
        .section.active { display: block; }
        .form-group { margin-bottom: 15px; }
        .form-group label { display: block; margin-bottom: 5px; font-weight: bold; }
        .form-group input, .form-group textarea { width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px; }
        .btn { padding: 10px 20px; background: #28a745; color: white; border: none; border-radius: 4px; cursor: pointer; }
        .btn:hover { background: #218838; }
        .btn-danger { background: #dc3545; }
        .btn-danger:hover { background: #c82333; }
        .alert { padding: 10px; margin: 10px 0; border-radius: 4px; }
        .alert-success { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
        .alert-error { background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
        .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 20px; }
        .stat-card { background: #f8f9fa; padding: 20px; border-radius: 8px; text-align: center; border-left: 4px solid #007bff; }
        .stat-value { font-size: 2em; font-weight: bold; color: #007bff; }
        .table { width: 100%; border-collapse: collapse; margin-top: 20px; }
        .table th, .table td { padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }
        .table th { background-color: #f8f9fa; font-weight: bold; }
        .table tr:hover { background-color: #f5f5f5; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Aadhaar UID Masking - Admin Dashboard</h1>
            <p>Manage API keys and view analytics</p>
        </div>
        
        <div class="nav">
            <button onclick="showSection('overview')">Overview</button>
            <button onclick="showSection('create-key')">Create API Key</button>
            <button onclick="showSection('manage-keys')">Manage Keys</button>
            <button onclick="showSection('analytics')">Analytics</button>
        </div>
        
        <div id="overview" class="section active">
            <h2>System Overview</h2>
            <div class="stats-grid" id="stats-container">
                <div class="stat-card">
                    <div class="stat-value" id="total-keys">-</div>
                    <div>Total API Keys</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value" id="active-keys">-</div>
                    <div>Active Keys</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value" id="total-requests">-</div>
                    <div>Total Requests</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value" id="success-rate">-</div>
                    <div>Success Rate</div>
                </div>
            </div>
        </div>
        
        <div id="create-key" class="section">
            <h2>Create New API Key</h2>
            <form id="create-key-form">
                <div class="form-group">
                    <label for="consumer_name">Consumer Name:</label>
                    <input type="text" id="consumer_name" name="consumer_name" required>
                </div>
                <div class="form-group">
                    <label for="consumer_email">Consumer Email:</label>
                    <input type="email" id="consumer_email" name="consumer_email" required>
                </div>
                <div class="form-group">
                    <label for="description">Description (Optional):</label>
                    <textarea id="description" name="description" rows="3"></textarea>
                </div>
                <button type="submit" class="btn">Generate API Key</button>
            </form>
            <div id="create-result"></div>
        </div>
        
        <div id="manage-keys" class="section">
            <h2>Manage API Keys</h2>
            <button onclick="loadAPIKeys()" class="btn">Refresh List</button>
            <div id="api-keys-container"></div>
        </div>
        
        <div id="analytics" class="section">
            <h2>System Analytics</h2>
            <button onclick="loadAnalytics()" class="btn">Refresh Analytics</button>
            <div id="analytics-container"></div>
        </div>
    </div>

    <script>
        // Show/hide sections
        function showSection(sectionId) {
            document.querySelectorAll('.section').forEach(section => {
                section.classList.remove('active');
            });
            document.getElementById(sectionId).classList.add('active');
            
            // Load data when section is shown
            if (sectionId === 'overview') {
                loadOverview();
            } else if (sectionId === 'manage-keys') {
                loadAPIKeys();
            } else if (sectionId === 'analytics') {
                loadAnalytics();
            }
        }
        
        // Load overview stats
        async function loadOverview() {
            try {
                const response = await fetch('/admin/analytics', {
                    headers: {
                        'Authorization': 'Basic ' + btoa('admin123:admin123')
                    }
                });
                const data = await response.json();
                
                document.getElementById('total-keys').textContent = data.total_api_keys || 0;
                document.getElementById('active-keys').textContent = data.active_api_keys || 0;
                document.getElementById('total-requests').textContent = data.total_requests || 0;
                document.getElementById('success-rate').textContent = (data.success_rate || 0) + '%';
            } catch (error) {
                console.error('Error loading overview:', error);
            }
        }
        
        // Create API key form handler
        document.getElementById('create-key-form').addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const formData = new FormData(e.target);
            const data = {
                consumer_name: formData.get('consumer_name'),
                consumer_email: formData.get('consumer_email'),
                description: formData.get('description')
            };
            
            try {
                const response = await fetch('/admin/api-keys', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': 'Basic ' + btoa('admin123:admin123')
                    },
                    body: JSON.stringify(data)
                });
                
                const result = await response.json();
                
                if (response.ok) {
                    document.getElementById('create-result').innerHTML = `
                        <div class="alert alert-success">
                            <h3>API Key Created Successfully!</h3>
                            <p><strong>API Key:</strong> <code>${result.api_key}</code></p>
                            <p><strong>Consumer:</strong> ${result.consumer_name}</p>
                            <p style="color: red;"><strong>Important:</strong> Save this API key securely. It will not be shown again!</p>
                        </div>
                    `;
                    e.target.reset();
                } else {
                    document.getElementById('create-result').innerHTML = `
                        <div class="alert alert-error">
                            <strong>Error:</strong> ${result.detail || 'Failed to create API key'}
                        </div>
                    `;
                }
            } catch (error) {
                document.getElementById('create-result').innerHTML = `
                    <div class="alert alert-error">
                        <strong>Error:</strong> ${error.message}
                    </div>
                `;
            }
        });
        
        // Load API keys
        async function loadAPIKeys() {
            try {
                const response = await fetch('/admin/api-keys?include_inactive=true', {
                    headers: {
                        'Authorization': 'Basic ' + btoa('admin123:admin123')
                    }
                });
                const data = await response.json();
                
                let html = '<table class="table"><thead><tr><th>Consumer Name</th><th>Email</th><th>Created</th><th>Status</th><th>Requests</th><th>Actions</th></tr></thead><tbody>';
                
                data.api_keys.forEach(key => {
                    html += `
                        <tr>
                            <td>${key.consumer_name}</td>
                            <td>${key.consumer_email}</td>
                            <td>${new Date(key.created_at).toLocaleDateString()}</td>
                            <td>${key.is_active ? '<span style="color: green;">Active</span>' : '<span style="color: red;">Inactive</span>'}</td>
                            <td>${key.total_requests} (${key.successful_requests} success, ${key.failed_requests} failed)</td>
                            <td>
                                ${key.is_active ? 
                                    `<button class="btn btn-danger" onclick="deactivateKey('${key.id}')">Deactivate</button>` :
                                    `<button class="btn" onclick="activateKey('${key.id}')">Activate</button>`
                                }
                                <button class="btn" onclick="viewAnalytics('${key.id}')">Analytics</button>
                            </td>
                        </tr>
                    `;
                });
                
                html += '</tbody></table>';
                document.getElementById('api-keys-container').innerHTML = html;
            } catch (error) {
                document.getElementById('api-keys-container').innerHTML = `
                    <div class="alert alert-error">Error loading API keys: ${error.message}</div>
                `;
            }
        }
        
        // Deactivate API key
        async function deactivateKey(keyId) {
            if (confirm('Are you sure you want to deactivate this API key?')) {
                try {
                    const response = await fetch(`/admin/api-keys/${keyId}/deactivate`, {
                        method: 'POST',
                        headers: {
                            'Authorization': 'Basic ' + btoa('admin123:admin123')
                        }
                    });
                    
                    if (response.ok) {
                        alert('API key deactivated successfully');
                        loadAPIKeys();
                    } else {
                        alert('Failed to deactivate API key');
                    }
                } catch (error) {
                    alert('Error: ' + error.message);
                }
            }
        }
        
        // Activate API key
        async function activateKey(keyId) {
            try {
                const response = await fetch(`/admin/api-keys/${keyId}/activate`, {
                    method: 'POST',
                    headers: {
                        'Authorization': 'Basic ' + btoa('admin123:admin123')
                    }
                });
                
                if (response.ok) {
                    alert('API key activated successfully');
                    loadAPIKeys();
                } else {
                    alert('Failed to activate API key');
                }
            } catch (error) {
                alert('Error: ' + error.message);
            }
        }
        
        // Load analytics
        async function loadAnalytics() {
            try {
                const response = await fetch('/admin/analytics', {
                    headers: {
                        'Authorization': 'Basic ' + btoa('admin123:admin123')
                    }
                });
                const data = await response.json();
                
                let html = `
                    <div class="stats-grid">
                        <div class="stat-card">
                            <div class="stat-value">${data.requests_today || 0}</div>
                            <div>Requests Today</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-value">${data.requests_this_week || 0}</div>
                            <div>Requests This Week</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-value">${data.requests_this_month || 0}</div>
                            <div>Requests This Month</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-value">${data.average_processing_time || 0}s</div>
                            <div>Avg Processing Time</div>
                        </div>
                    </div>
                    <h3>System Details</h3>
                    <table class="table">
                        <tr><td>Total API Keys</td><td>${data.total_api_keys || 0}</td></tr>
                        <tr><td>Active API Keys</td><td>${data.active_api_keys || 0}</td></tr>
                        <tr><td>Total Requests</td><td>${data.total_requests || 0}</td></tr>
                        <tr><td>Successful Requests</td><td>${data.successful_requests || 0}</td></tr>
                        <tr><td>Failed Requests</td><td>${data.failed_requests || 0}</td></tr>
                        <tr><td>Success Rate</td><td>${data.success_rate || 0}%</td></tr>
                        <tr><td>Last Updated</td><td>${new Date(data.last_updated).toLocaleString()}</td></tr>
                    </table>
                `;
                
                document.getElementById('analytics-container').innerHTML = html;
            } catch (error) {
                document.getElementById('analytics-container').innerHTML = `
                    <div class="alert alert-error">Error loading analytics: ${error.message}</div>
                `;
            }
        }
        
        // View analytics for a specific API key
        async function viewAnalytics(keyId) {
            try {
                const response = await fetch(`/admin/api-keys/${keyId}/analytics`, {
                    headers: {
                        'Authorization': 'Basic ' + btoa('admin123:admin123')
                    }
                });
                
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }
                
                const data = await response.json();
                
                // Create modal HTML
                const modalHTML = `
                    <div style="position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); z-index: 1000; display: flex; align-items: center; justify-content: center;" id="analytics-modal">
                        <div style="background: white; padding: 30px; border-radius: 10px; max-width: 600px; max-height: 80vh; overflow-y: auto; position: relative;">
                            <span style="position: absolute; top: 15px; right: 20px; font-size: 24px; cursor: pointer; color: #999;" onclick="closeAnalyticsModal()">×</span>
                            <h2>📊 API Key Analytics</h2>
                            <p><strong>Consumer:</strong> ${data.consumer_name}</p>
                            <p><strong>Email:</strong> ${data.consumer_email}</p>
                            <p><strong>Status:</strong> <span style="color: ${data.is_active ? 'green' : 'red'};">${data.is_active ? 'Active' : 'Inactive'}</span></p>
                            
                            <div class="stats-grid" style="margin: 20px 0;">
                                <div class="stat-card">
                                    <div class="stat-value">${data.total_requests || 0}</div>
                                    <div>Total Requests</div>
                                </div>
                                <div class="stat-card">
                                    <div class="stat-value">${data.successful_requests || 0}</div>
                                    <div>Successful</div>
                                </div>
                                <div class="stat-card">
                                    <div class="stat-value">${data.failed_requests || 0}</div>
                                    <div>Failed</div>
                                </div>
                                <div class="stat-card">
                                    <div class="stat-value">${data.success_rate || 0}%</div>
                                    <div>Success Rate</div>
                                </div>
                            </div>
                            
                            <h3>📈 Usage Details</h3>
                            <table class="table" style="margin-top: 15px;">
                                <tr><td>Created</td><td>${new Date(data.created_at).toLocaleString()}</td></tr>
                                <tr><td>Last Used</td><td>${data.last_used ? new Date(data.last_used).toLocaleString() : 'Never'}</td></tr>
                                <tr><td>Average Processing Time</td><td>${data.average_processing_time || 0}s</td></tr>
                                <tr><td>Total Processing Time</td><td>${data.total_processing_time || 0}s</td></tr>
                                <tr><td>Requests Today</td><td>${data.requests_today || 0}</td></tr>
                                <tr><td>Requests This Week</td><td>${data.requests_this_week || 0}</td></tr>
                                <tr><td>Requests This Month</td><td>${data.requests_this_month || 0}</td></tr>
                            </table>
                            
                            ${data.recent_requests && data.recent_requests.length > 0 ? `
                                <h3>📋 Recent Activity</h3>
                                <div style="max-height: 200px; overflow-y: auto; margin-top: 15px;">
                                    ${data.recent_requests.map(req => `
                                        <div style="padding: 8px; border-left: 3px solid ${req.status === 'success' ? '#28a745' : '#dc3545'}; margin-bottom: 8px; background: #f8f9fa;">
                                            <strong>${req.endpoint}</strong> - ${req.status}
                                            <br><small>${new Date(req.timestamp).toLocaleString()} (${req.processing_time}s)</small>
                                        </div>
                                    `).join('')}
                                </div>
                            ` : ''}
                            
                            <div style="text-align: center; margin-top: 20px;">
                                <button class="btn" onclick="closeAnalyticsModal()">Close</button>
                            </div>
                        </div>
                    </div>
                `;
                
                // Add modal to page
                document.body.insertAdjacentHTML('beforeend', modalHTML);
                
            } catch (error) {
                alert(`Error loading analytics: ${error.message}`);
                console.error('Analytics error:', error);
            }
        }
        
        // Close analytics modal
        function closeAnalyticsModal() {
            const modal = document.getElementById('analytics-modal');
            if (modal) {
                modal.remove();
            }
        }
        
        // Load overview on page load
        loadOverview();
    </script>
</body>
</html>
    """

@app.post("/admin/api-keys", response_model=APIKeyResponse)
async def create_api_key(
    api_key_data: APIKeyCreate,
    admin_auth: bool = Depends(authenticate_admin)
):
    """Create a new API key for a consumer."""
    try:
        api_key_id, api_key = await api_key_manager.generate_api_key(
            consumer_name=api_key_data.consumer_name,
            consumer_email=api_key_data.consumer_email,
            description=api_key_data.description
        )
        
        # Get the created API key data
        api_key_doc = await db_manager.db.api_keys.find_one({"_id": ObjectId(api_key_id)})
        
        response = APIKeyResponse(
            id=api_key_id,
            api_key=api_key,  # Only returned once during creation
            consumer_name=api_key_doc["consumer_name"],
            consumer_email=api_key_doc["consumer_email"],
            description=api_key_doc.get("description"),
            is_active=api_key_doc["is_active"],
            created_at=api_key_doc["created_at"],
            last_used=api_key_doc.get("last_used"),
            total_requests=api_key_doc["total_requests"],
            successful_requests=api_key_doc["successful_requests"],
            failed_requests=api_key_doc["failed_requests"]
        )
        
        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/admin/api-keys", response_model=APIKeyListResponse)
async def list_api_keys(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    include_inactive: bool = Query(False),
    admin_auth: bool = Depends(authenticate_admin)
):
    """List all API keys with pagination."""
    try:
        skip = (page - 1) * page_size
        api_keys, total_count = await api_key_manager.list_api_keys(
            skip=skip,
            limit=page_size,
            include_inactive=include_inactive
        )
        
        # Convert to response format (without exposing actual API keys)
        api_key_responses = []
        for key_doc in api_keys:
            response = APIKeyResponse(
                id=key_doc["id"],
                api_key="***HIDDEN***",  # Never expose actual API keys in listings
                consumer_name=key_doc["consumer_name"],
                consumer_email=key_doc["consumer_email"],
                description=key_doc.get("description"),
                is_active=key_doc["is_active"],
                created_at=key_doc["created_at"],
                last_used=key_doc.get("last_used"),
                total_requests=key_doc["total_requests"],
                successful_requests=key_doc["successful_requests"],
                failed_requests=key_doc["failed_requests"]
            )
            api_key_responses.append(response)
        
        total_pages = (total_count + page_size - 1) // page_size
        
        return APIKeyListResponse(
            api_keys=api_key_responses,
            total_count=total_count,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/admin/api-keys/{api_key_id}/deactivate")
async def deactivate_api_key(
    api_key_id: str,
    admin_auth: bool = Depends(authenticate_admin)
):
    """Deactivate an API key."""
    try:
        logger.info(f"Attempting to deactivate API key: {api_key_id}")
        
        # Validate API key ID format
        if not api_key_id:
            logger.error("Empty API key ID provided")
            raise HTTPException(status_code=400, detail="API key ID cannot be empty")
        
        # Auto-convert if they provided the actual API key instead of ID
        if len(api_key_id) == 64:
            logger.info("64-character API key provided, converting to API key ID")
            # Look up the API key ID from the actual API key
            key_hash = api_key_manager._hash_api_key(api_key_id)
            api_key_doc = await db_manager.db.api_keys.find_one({"key_hash": key_hash})
            
            if not api_key_doc:
                raise HTTPException(
                    status_code=404, 
                    detail="API key not found in database. Please check the API key value."
                )
            
            # Convert to the correct ID format
            api_key_id = str(api_key_doc["_id"])
            logger.info(f"Converted to API key ID: {api_key_id}")
            
        elif len(api_key_id) != 24:
            logger.error(f"Invalid API key ID format: {api_key_id} (length: {len(api_key_id)})")
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid format. Expected either:\n- API key ID (24 characters): Use the 'id' field from API key creation\n- API key (64 characters): Use the 'api_key' field from API key creation\nYou provided {len(api_key_id)} characters."
            )
        
        # Additional validation to ensure it's a valid ObjectId format
        try:
            from bson import ObjectId
            ObjectId(api_key_id)
        except Exception as e:
            logger.error(f"Invalid ObjectId format: {api_key_id} - {e}")
            raise HTTPException(
                status_code=400,
                detail=f"Invalid API key ID format. Must be a valid MongoDB ObjectId (24-character hex string)."
            )
        
        success = await api_key_manager.deactivate_api_key(api_key_id)
        
        if not success:
            logger.error(f"API key not found for deactivation: {api_key_id}")
            raise HTTPException(status_code=404, detail="API key not found")
        
        logger.info(f"Successfully deactivated API key: {api_key_id}")
        return {"message": f"API key {api_key_id} deactivated successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error deactivating API key {api_key_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

@app.post("/admin/api-keys/{api_key_id}/activate")
async def activate_api_key(
    api_key_id: str,
    admin_auth: bool = Depends(authenticate_admin)
):
    """Reactivate an API key."""
    try:
        logger.info(f"Attempting to activate API key: {api_key_id}")
        
        # Validate API key ID format
        if not api_key_id:
            logger.error("Empty API key ID provided")
            raise HTTPException(status_code=400, detail="API key ID cannot be empty")
        
        # Auto-convert if they provided the actual API key instead of ID
        if len(api_key_id) == 64:
            logger.info("64-character API key provided, converting to API key ID")
            # Look up the API key ID from the actual API key
            key_hash = api_key_manager._hash_api_key(api_key_id)
            api_key_doc = await db_manager.db.api_keys.find_one({"key_hash": key_hash})
            
            if not api_key_doc:
                raise HTTPException(
                    status_code=404, 
                    detail="API key not found in database. Please check the API key value."
                )
            
            # Convert to the correct ID format
            api_key_id = str(api_key_doc["_id"])
            logger.info(f"Converted to API key ID: {api_key_id}")
            
        elif len(api_key_id) != 24:
            logger.error(f"Invalid API key ID format: {api_key_id} (length: {len(api_key_id)})")
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid format. Expected either:\n- API key ID (24 characters): Use the 'id' field from API key creation\n- API key (64 characters): Use the 'api_key' field from API key creation\nYou provided {len(api_key_id)} characters."
            )
        
        # Additional validation to ensure it's a valid ObjectId format
        try:
            from bson import ObjectId
            ObjectId(api_key_id)
        except Exception as e:
            logger.error(f"Invalid ObjectId format: {api_key_id} - {e}")
            raise HTTPException(
                status_code=400,
                detail=f"Invalid API key ID format. Must be a valid MongoDB ObjectId (24-character hex string)."
            )
        
        success = await api_key_manager.reactivate_api_key(api_key_id)
        
        if not success:
            logger.error(f"API key not found for activation: {api_key_id}")
            raise HTTPException(status_code=404, detail="API key not found")
        
        logger.info(f"Successfully activated API key: {api_key_id}")
        return {"message": f"API key {api_key_id} activated successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error activating API key {api_key_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

@app.get("/admin/api-keys/{api_key_id}/analytics")
async def get_api_key_analytics(
    api_key_id: str,
    admin_auth: bool = Depends(authenticate_admin)
):
    """Get analytics for a specific API key."""
    try:
        logger.info(f"Getting analytics for API key: {api_key_id}")
        
        # Auto-convert if they provided the actual API key instead of ID
        if len(api_key_id) == 64:
            logger.info("64-character API key provided, converting to API key ID")
            # Look up the API key ID from the actual API key
            key_hash = api_key_manager._hash_api_key(api_key_id)
            api_key_doc = await db_manager.db.api_keys.find_one({"key_hash": key_hash})
            
            if not api_key_doc:
                raise HTTPException(
                    status_code=404, 
                    detail="API key not found in database. Please check the API key value."
                )
            
            # Convert to the correct ID format
            api_key_id = str(api_key_doc["_id"])
            logger.info(f"Converted to API key ID: {api_key_id}")
            
        elif len(api_key_id) != 24:
            logger.error(f"Invalid API key ID format: {api_key_id} (length: {len(api_key_id)})")
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid format. Expected either:\n- API key ID (24 characters): Use the 'id' field from API key creation\n- API key (64 characters): Use the 'api_key' field from API key creation\nYou provided {len(api_key_id)} characters."
            )
        
        # Get the API key document directly from database to ensure we have all fields
        try:
            object_id = ObjectId(api_key_id)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid API key ID format")
        
        api_key_doc = await db_manager.db.api_keys.find_one({"_id": object_id})
        if not api_key_doc:
            raise HTTPException(status_code=404, detail="API key not found")
        
        # Get request logs for additional analytics
        request_logs = await db_manager.db.request_logs.find({
            "api_key_id": object_id
        }).sort("timestamp", -1).limit(10).to_list(10)
        
        # Calculate total processing time
        total_processing_time = 0
        if request_logs:
            for log in request_logs:
                if log.get("processing_time"):
                    total_processing_time += log["processing_time"]
        
        # Calculate success rate
        total_requests = api_key_doc.get("total_requests", 0)
        successful_requests = api_key_doc.get("successful_requests", 0)
        failed_requests = api_key_doc.get("failed_requests", 0)
        
        success_rate = 0
        if total_requests > 0:
            success_rate = round((successful_requests / total_requests) * 100, 1)
        
        # Format recent requests for frontend
        recent_requests = []
        for log in request_logs:
            recent_requests.append({
                "timestamp": log.get("timestamp", datetime.now().isoformat()),
                "endpoint": log.get("endpoint", "unknown"),
                "status": log.get("status", "unknown"),
                "processing_time": log.get("processing_time", 0)
            })
        
        # Calculate time-based request counts
        now = datetime.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today_start - timedelta(days=now.weekday())
        month_start = today_start.replace(day=1)
        
        # Count requests for different time periods
        requests_today = 0
        requests_this_week = 0
        requests_this_month = 0
        
        for log in request_logs:
            log_time = log.get("timestamp")
            if log_time:
                if isinstance(log_time, str):
                    log_time = datetime.fromisoformat(log_time.replace('Z', '+00:00'))
                elif hasattr(log_time, 'replace'):
                    # It's already a datetime object
                    pass
                else:
                    continue
                
                # Remove timezone info for comparison
                if log_time.tzinfo:
                    log_time = log_time.replace(tzinfo=None)
                
                if log_time >= today_start:
                    requests_today += 1
                if log_time >= week_start:
                    requests_this_week += 1
                if log_time >= month_start:
                    requests_this_month += 1
        
        # Build comprehensive analytics response
        analytics = {
            "api_key_id": api_key_id,
            "consumer_name": api_key_doc.get("consumer_name", "Unknown"),
            "consumer_email": api_key_doc.get("consumer_email", "Unknown"),
            "is_active": api_key_doc.get("is_active", False),
            "created_at": api_key_doc.get("created_at", datetime.now().isoformat()),
            "last_used": api_key_doc.get("last_used", None),
            "total_requests": total_requests,
            "successful_requests": successful_requests,
            "failed_requests": failed_requests,
            "success_rate": success_rate,
            "average_processing_time": round(total_processing_time / max(successful_requests, 1), 3),
            "total_processing_time": round(total_processing_time, 3),
            "requests_today": requests_today,
            "requests_this_week": requests_this_week,
            "requests_this_month": requests_this_month,
            "recent_requests": recent_requests
        }
        
        logger.info(f"Retrieved analytics for API key: {api_key_id}")
        return analytics
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting analytics for API key {api_key_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/admin/analytics")
async def get_system_analytics(admin_auth: bool = Depends(authenticate_admin)):
    """Get system-wide analytics."""
    try:
        analytics = await api_key_manager.get_system_analytics()
        return analytics
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/admin/debug/api-keys")
async def debug_api_keys(admin_auth: bool = Depends(authenticate_admin)):
    """Debug endpoint to check API keys in database."""
    try:
        logger.info("Debug endpoint called - checking API keys in database")
        
        # Get all API keys (including inactive)
        api_keys, total_count = await api_key_manager.list_api_keys(
            skip=0,
            limit=100,
            include_inactive=True
        )
        
        # Format for debugging
        debug_info = {
            "total_api_keys": total_count,
            "api_keys": []
        }
        
        for key in api_keys:
            debug_info["api_keys"].append({
                "id": key["id"],
                "consumer_name": key["consumer_name"],
                "consumer_email": key["consumer_email"],
                "is_active": key["is_active"],
                "created_at": key["created_at"],
                "total_requests": key["total_requests"]
            })
        
        logger.info(f"Debug: Found {total_count} API keys in database")
        return debug_info
        
    except Exception as e:
        logger.error(f"Debug endpoint error: {e}")
        raise HTTPException(status_code=500, detail=f"Debug error: {str(e)}")

@app.get("/admin/lookup-api-key-id/{api_key}")
async def lookup_api_key_id(api_key: str, admin_auth: bool = Depends(authenticate_admin)):
    """Look up API key ID by providing the actual API key."""
    try:
        logger.info(f"Looking up API key ID for provided API key: {api_key[:8]}...")
        
        # Validate the API key format
        if len(api_key) != 64:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid API key format. Expected 64 characters, got {len(api_key)} characters."
            )
        
        # Find the API key in database by hash
        from api_key_manager import api_key_manager
        key_hash = api_key_manager._hash_api_key(api_key)
        
        api_key_doc = await db_manager.db.api_keys.find_one({
            "key_hash": key_hash
        })
        
        if not api_key_doc:
            raise HTTPException(status_code=404, detail="API key not found in database")
        
        result = {
            "api_key_id": str(api_key_doc["_id"]),
            "consumer_name": api_key_doc["consumer_name"],
            "consumer_email": api_key_doc["consumer_email"],
            "is_active": api_key_doc["is_active"],
            "created_at": api_key_doc["created_at"],
            "message": f"Use this API key ID for deactivation/activation: {str(api_key_doc['_id'])}"
        }
        
        logger.info(f"Found API key ID: {str(api_key_doc['_id'])} for consumer: {api_key_doc['consumer_name']}")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error looking up API key ID: {e}")
        raise HTTPException(status_code=500, detail=f"Lookup error: {str(e)}")

@app.get("/admin/debug/request-logs/{api_key_identifier}")
async def debug_request_logs(api_key_identifier: str, admin_auth: bool = Depends(authenticate_admin)):
    """Debug endpoint to check request logs for a specific API key."""
    try:
        logger.info(f"Debugging request logs for: {api_key_identifier}")
        
        # Convert to API key ID if needed
        if len(api_key_identifier) == 64:
            # Look up the API key ID from the actual API key
            key_hash = api_key_manager._hash_api_key(api_key_identifier)
            api_key_doc = await db_manager.db.api_keys.find_one({"key_hash": key_hash})
            
            if not api_key_doc:
                raise HTTPException(status_code=404, detail="API key not found in database")
            
            api_key_id = str(api_key_doc["_id"])
            object_id = api_key_doc["_id"]
        elif len(api_key_identifier) == 24:
            api_key_id = api_key_identifier
            try:
                from bson import ObjectId
                object_id = ObjectId(api_key_identifier)
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Invalid ObjectId format: {e}")
        else:
            raise HTTPException(status_code=400, detail="Invalid API key or API key ID format")
        
        # Get API key info
        api_key_doc = await db_manager.db.api_keys.find_one({"_id": object_id})
        if not api_key_doc:
            raise HTTPException(status_code=404, detail="API key not found")
        
        # Get request logs
        request_logs = await db_manager.db.request_logs.find({
            "api_key_id": object_id
        }).sort("timestamp", -1).limit(10).to_list(10)
        
        # Get total counts
        total_logs = await db_manager.db.request_logs.count_documents({"api_key_id": object_id})
        
        # Format logs for debugging
        formatted_logs = []
        for log in request_logs:
            formatted_logs.append({
                "timestamp": log["timestamp"],
                "endpoint": log["endpoint"],
                "status": log["status"],
                "processing_time": log["processing_time"],
                "error_message": log.get("error_message"),
                "file_size": log.get("file_size"),
                "locations_found": log.get("locations_found")
            })
        
        debug_info = {
            "api_key_id": api_key_id,
            "consumer_name": api_key_doc["consumer_name"],
            "api_key_stats": {
                "total_requests": api_key_doc["total_requests"],
                "successful_requests": api_key_doc["successful_requests"],
                "failed_requests": api_key_doc["failed_requests"],
                "last_used": api_key_doc.get("last_used")
            },
            "request_logs_count": total_logs,
            "recent_logs": formatted_logs,
            "collections_info": {
                "api_keys_count": await db_manager.db.api_keys.count_documents({}),
                "request_logs_count": await db_manager.db.request_logs.count_documents({})
            }
        }
        
        logger.info(f"Debug: Found {total_logs} request logs for API key {api_key_id}")
        return debug_info
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Debug request logs error: {e}")
        raise HTTPException(status_code=500, detail=f"Debug error: {str(e)}")

# ==== Authenticated API Endpoints (API Key Required) ====

@app.post("/process-image", response_model=ProcessResult)
async def process_image(
    request: Request, 
    file: UploadFile = File(...), 
    store: bool = Query(False, description="Store processed image in database"),
    consumer_data: dict = Depends(authenticate_api_key)
):
    """
    Process a single image to detect and mask Aadhaar numbers.
    Requires API key authentication.
    """
    start_time = datetime.now()
    
    # Validate file type
    if not file.content_type or not file.content_type.startswith('image/'):
        await log_api_request(
            request, "/process-image", 
            (datetime.now() - start_time).total_seconds(),
            "failed", "Invalid file type"
        )
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
                    "image_format": file.content_type or "unknown",
                    "consumer_name": consumer_data["consumer_name"],
                    "consumer_email": consumer_data["consumer_email"]
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
        
        # Log successful request
        await log_api_request(
            request, "/process-image",
            result.processing_time, "success",
            file_size=upload_path.stat().st_size,
            locations_found=result.locations_found
        )
        
        return result
        
    except HTTPException as e:
        # Log failed request
        await log_api_request(
            request, "/process-image",
            (datetime.now() - start_time).total_seconds(),
            "failed", str(e.detail)
        )
        raise
    except Exception as e:
        # Log failed request
        await log_api_request(
            request, "/process-image",
            (datetime.now() - start_time).total_seconds(),
            "failed", str(e)
        )
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")
    finally:
        # Clean up uploaded file
        if upload_path.exists():
            upload_path.unlink()

@app.post("/process-bulk", response_model=BulkProcessResult)
async def process_bulk_images(
    request: Request, 
    files: List[UploadFile] = File(...),
    consumer_data: dict = Depends(authenticate_api_key)
):
    """
    Process multiple images to detect and mask Aadhaar numbers.
    Requires API key authentication.
    """
    start_time = datetime.now()
    
    if not files:
        await log_api_request(
            request, "/process-bulk",
            (datetime.now() - start_time).total_seconds(),
            "failed", "No files provided"
        )
        raise HTTPException(status_code=400, detail="No files provided")
    
    if len(files) > 10:  # Limit bulk processing
        await log_api_request(
            request, "/process-bulk",
            (datetime.now() - start_time).total_seconds(),
            "failed", "Too many files"
        )
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
    
    # Log request
    status = "success" if successful_processes > 0 else "failed"
    error_msg = "; ".join(errors) if errors else None
    
    await log_api_request(
        request, "/process-bulk",
        (datetime.now() - start_time).total_seconds(),
        status, error_msg
    )
    
    return bulk_result

@app.get("/download/{filename}")
async def download_file(filename: str):
    """
    Download a processed image file with proper headers for browser download.
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
async def cleanup_files(admin_auth: bool = Depends(authenticate_admin)):
    """
    Clean up old processed files (admin endpoint).
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

# Database Storage Endpoints (require API key authentication)

@app.post("/process-and-store-image", response_model=ProcessResult)
async def process_and_store_image(
    request: Request, 
    file: UploadFile = File(...),
    consumer_data: dict = Depends(authenticate_api_key)
):
    """
    Process a single image and automatically store in database with encryption.
    Requires API key authentication.
    """
    start_time = datetime.now()
    
    # Validate file type
    if not file.content_type or not file.content_type.startswith('image/'):
        await log_api_request(
            request, "/process-and-store-image",
            (datetime.now() - start_time).total_seconds(),
            "failed", "Invalid file type"
        )
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
            "image_format": file.content_type or "unknown",
            "consumer_name": consumer_data["consumer_name"],
            "consumer_email": consumer_data["consumer_email"]
        }
        
        record_id = await secure_storage.store_processed_card(
            original_image_path=str(upload_path),
            masked_image_path=str(STATIC_DIR / masked_filename),
            aadhaar_number=result.uid_numbers[0],
            filename=file.filename,
            processing_metadata=processing_metadata
        )
        
        result.record_id = str(record_id)
        
        # Log successful request
        await log_api_request(
            request, "/process-and-store-image",
            result.processing_time, "success",
            file_size=upload_path.stat().st_size,
            locations_found=result.locations_found
        )
        
        return result
        
    except HTTPException as e:
        await log_api_request(
            request, "/process-and-store-image",
            (datetime.now() - start_time).total_seconds(),
            "failed", str(e.detail)
        )
        raise
    except Exception as e:
        await log_api_request(
            request, "/process-and-store-image",
            (datetime.now() - start_time).total_seconds(),
            "failed", str(e)
        )
        raise HTTPException(status_code=500, detail=f"Processing and storage error: {str(e)}")
    finally:
        # Clean up uploaded file
        if upload_path.exists():
            upload_path.unlink()

# ==== Records and Statistics Endpoints (Public - for frontend) ====

@app.get("/list-records")
async def list_records(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Number of records per page")
):
    """
    List stored processed records with pagination.
    Public endpoint for frontend Records tab.
    """
    try:
        logger.info(f"Listing records - page: {page}, page_size: {page_size}")
        
        # Check if database is connected
        if not db_manager._connection_validated:
            return {
                "records": [],
                "total": 0,
                "page": page,
                "page_size": page_size,
                "total_pages": 0,
                "message": "Database not connected - no records available"
            }
        
        # Calculate skip value
        skip = (page - 1) * page_size
        
        # Get records from secure storage or database
        if hasattr(secure_storage, 'list_stored_records'):
            # Use secure storage if available
            records, total_count = await secure_storage.list_stored_records(
                skip=skip,
                limit=page_size
            )
        else:
            # Fallback to direct database query
            # Look for processed cards collection
            collections = await db_manager.db.list_collection_names()
            if "processed_cards" in collections:
                cursor = db_manager.db.processed_cards.find({}).skip(skip).limit(page_size)
                records = await cursor.to_list(page_size)
                total_count = await db_manager.db.processed_cards.count_documents({})
            else:
                records = []
                total_count = 0
        
        # Format records for frontend
        formatted_records = []
        for record in records:
            formatted_record = {
                "id": str(record.get("_id", record.get("id", "unknown"))),
                "filename": record.get("filename", "unknown"),
                "created_at": record.get("created_at", record.get("processed_at", datetime.now().isoformat())),
                "processing_time": record.get("processing_metadata", {}).get("processing_time", 0),
                "locations_found": record.get("processing_metadata", {}).get("locations_found", 0),
                "consumer_name": record.get("processing_metadata", {}).get("consumer_name", "Unknown"),
                "file_size": record.get("processing_metadata", {}).get("file_size_original", 0),
                "status": "completed"
            }
            formatted_records.append(formatted_record)
        
        # Calculate pagination info
        total_pages = (total_count + page_size - 1) // page_size
        
        response = {
            "records": formatted_records,
            "total": total_count,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1
        }
        
        logger.info(f"Retrieved {len(formatted_records)} records (total: {total_count})")
        return response
        
    except Exception as e:
        logger.error(f"Error listing records: {e}")
        # Return empty result instead of error to prevent frontend crash
        return {
            "records": [],
            "total": 0,
            "page": page,
            "page_size": page_size,
            "total_pages": 0,
            "error": f"Failed to load records: {str(e)}"
        }

@app.get("/statistics")
async def get_statistics():
    """
    Get general system statistics for frontend dashboard.
    Public endpoint for frontend Records tab.
    """
    try:
        logger.info("Getting system statistics")
        
        # Check if database is connected
        if not db_manager._connection_validated:
            return {
                "total_processed": 0,
                "total_api_keys": 0,
                "total_requests": 0,
                "success_rate": 100.0,
                "avg_processing_time": 0.0,
                "recent_activity": [],
                "message": "Database not connected - statistics unavailable"
            }
        
        # Get collection names
        collections = await db_manager.db.list_collection_names()
        
        # Initialize statistics
        stats = {
            "total_processed": 0,
            "total_api_keys": 0,
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "success_rate": 100.0,
            "avg_processing_time": 0.0,
            "recent_activity": []
        }
        
        # Get processed cards count
        if "processed_cards" in collections:
            stats["total_processed"] = await db_manager.db.processed_cards.count_documents({})
        
        # Get API keys statistics
        if "api_keys" in collections:
            stats["total_api_keys"] = await db_manager.db.api_keys.count_documents({})
            
            # Get total requests from API keys
            pipeline = [
                {"$group": {
                    "_id": None,
                    "total_requests": {"$sum": "$total_requests"},
                    "successful_requests": {"$sum": "$successful_requests"},
                    "failed_requests": {"$sum": "$failed_requests"}
                }}
            ]
            result = await db_manager.db.api_keys.aggregate(pipeline).to_list(1)
            if result:
                stats["total_requests"] = result[0]["total_requests"]
                stats["successful_requests"] = result[0]["successful_requests"]
                stats["failed_requests"] = result[0]["failed_requests"]
        
        # Calculate success rate
        if stats["total_requests"] > 0:
            stats["success_rate"] = round(
                (stats["successful_requests"] / stats["total_requests"]) * 100, 1
            )
        
        # Get average processing time from request logs
        if "request_logs" in collections:
            pipeline = [
                {"$match": {"status": "success", "processing_time": {"$exists": True}}},
                {"$group": {
                    "_id": None,
                    "avg_processing_time": {"$avg": "$processing_time"}
                }}
            ]
            result = await db_manager.db.request_logs.aggregate(pipeline).to_list(1)
            if result and result[0]["avg_processing_time"]:
                stats["avg_processing_time"] = round(result[0]["avg_processing_time"], 2)
            
            # Get recent activity (last 10 requests)
            recent_logs = await db_manager.db.request_logs.find({}).sort("timestamp", -1).limit(10).to_list(10)
            for log in recent_logs:
                stats["recent_activity"].append({
                    "timestamp": log.get("timestamp", datetime.now().isoformat()),
                    "endpoint": log.get("endpoint", "unknown"),
                    "status": log.get("status", "unknown"),
                    "processing_time": log.get("processing_time", 0)
                })
        
        # Additional useful statistics
        stats.update({
            "database_connected": True,
            "collections_available": collections,
            "last_updated": datetime.now().isoformat()
        })
        
        logger.info(f"Statistics: {stats['total_processed']} processed, {stats['total_requests']} requests")
        return stats
        
    except Exception as e:
        logger.error(f"Error getting statistics: {e}")
        # Return basic stats instead of error
        return {
            "total_processed": 0,
            "total_api_keys": 0,
            "total_requests": 0,
            "success_rate": 0.0,
            "avg_processing_time": 0.0,
            "recent_activity": [],
            "database_connected": False,
            "error": f"Failed to load statistics: {str(e)}",
            "last_updated": datetime.now().isoformat()
        }

@app.get("/get-record/{record_id}")
async def get_record_details(record_id: str):
    """
    Get detailed information about a specific record.
    Public endpoint for frontend record viewing.
    """
    try:
        logger.info(f"Getting record details for ID: {record_id}")
        
        # Check if database is connected
        if not db_manager._connection_validated:
            raise HTTPException(status_code=503, detail="Database not connected")
        
        # Convert string ID to ObjectId
        try:
            object_id = ObjectId(record_id)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid record ID format")
        
        # Look for the record in processed_cards collection
        collections = await db_manager.db.list_collection_names()
        if "processed_cards" not in collections:
            raise HTTPException(status_code=404, detail="No records collection found")
        
        record = await db_manager.db.processed_cards.find_one({"_id": object_id})
        if not record:
            raise HTTPException(status_code=404, detail="Record not found")
        
        # Format the record for frontend
        formatted_record = {
            "id": str(record["_id"]),
            "filename": record.get("filename", "unknown"),
            "created_at": record.get("created_at", record.get("processed_at", datetime.now().isoformat())),
            "processing_time": record.get("processing_metadata", {}).get("processing_time", 0),
            "locations_found": record.get("processing_metadata", {}).get("locations_found", 0),
            "consumer_name": record.get("processing_metadata", {}).get("consumer_name", "Unknown"),
            "consumer_email": record.get("processing_metadata", {}).get("consumer_email", "Unknown"),
            "file_size_original": record.get("processing_metadata", {}).get("file_size_original", 0),
            "file_size_masked": record.get("processing_metadata", {}).get("file_size_masked", 0),
            "image_format": record.get("processing_metadata", {}).get("image_format", "unknown"),
            "status": "completed",
            # Don't include actual UID numbers for security (they're encrypted anyway)
            "uid_numbers": None  # This will show "Protected/Encrypted" in frontend
        }
        
        logger.info(f"Retrieved record details for: {formatted_record['filename']}")
        return formatted_record
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting record details: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve record: {str(e)}")

@app.get("/retrieve-image/{record_id}/{image_type}")
async def retrieve_stored_image(record_id: str, image_type: str):
    """
    Retrieve and download a stored image (original or masked).
    Public endpoint for frontend image downloads.
    """
    try:
        logger.info(f"Retrieving {image_type} image for record: {record_id}")
        
        # Validate image type
        if image_type not in ["original", "masked"]:
            raise HTTPException(status_code=400, detail="Image type must be 'original' or 'masked'")
        
        # Check if database is connected
        if not db_manager._connection_validated:
            raise HTTPException(status_code=503, detail="Database not connected")
        
        # Convert string ID to ObjectId
        try:
            object_id = ObjectId(record_id)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid record ID format")
        
        # Get the record
        record = await db_manager.db.processed_cards.find_one({"_id": object_id})
        if not record:
            raise HTTPException(status_code=404, detail="Record not found")
        
        # Use secure storage to retrieve the image
        if hasattr(secure_storage, 'retrieve_stored_image'):
            try:
                image_data = await secure_storage.retrieve_stored_image(record_id, image_type)
                if not image_data:
                    raise HTTPException(status_code=404, detail=f"{image_type.title()} image not found")
                
                # Return the image as a streaming response
                return StreamingResponse(
                    io.BytesIO(image_data),
                    media_type="image/jpeg",
                    headers={
                        "Content-Disposition": f"attachment; filename={image_type}_{record['filename']}",
                        "Cache-Control": "no-cache, no-store, must-revalidate"
                    }
                )
            except Exception as e:
                logger.error(f"Secure storage retrieval failed: {e}")
                # Fall through to alternative method
        
        # Alternative: Look for the file in static directory (for recently processed images)
        # This is a fallback for images that might not be in secure storage yet
        static_files = list(STATIC_DIR.glob(f"*{record['filename']}*"))
        if static_files:
            # Try to find the right file
            for file_path in static_files:
                if image_type == "masked" and "masked" in file_path.name:
                    return FileResponse(
                        path=str(file_path),
                        filename=f"masked_{record['filename']}",
                        media_type="image/jpeg",
                        headers={"Content-Disposition": f"attachment; filename=masked_{record['filename']}"}
                    )
                elif image_type == "original" and "masked" not in file_path.name:
                    return FileResponse(
                        path=str(file_path),
                        filename=record['filename'],
                        media_type="image/jpeg",
                        headers={"Content-Disposition": f"attachment; filename={record['filename']}"}
                    )
        
        # If we get here, the image wasn't found
        raise HTTPException(
            status_code=404, 
            detail=f"{image_type.title()} image not available. It may have been cleaned up or not stored properly."
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving image: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve image: {str(e)}")

@app.delete("/delete-record/{record_id}")
async def delete_stored_record(record_id: str):
    """
    Delete a stored record and its associated images.
    Public endpoint for frontend record deletion.
    """
    try:
        logger.info(f"Deleting record: {record_id}")
        
        # Check if database is connected
        if not db_manager._connection_validated:
            raise HTTPException(status_code=503, detail="Database not connected")
        
        # Convert string ID to ObjectId
        try:
            object_id = ObjectId(record_id)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid record ID format")
        
        # Get the record first to check if it exists
        record = await db_manager.db.processed_cards.find_one({"_id": object_id})
        if not record:
            raise HTTPException(status_code=404, detail="Record not found")
        
        # Use secure storage to delete the record if available
        if hasattr(secure_storage, 'delete_stored_record'):
            try:
                await secure_storage.delete_stored_record(record_id)
                logger.info(f"Successfully deleted record via secure storage: {record_id}")
                return {"message": "Record deleted successfully", "record_id": record_id}
            except Exception as e:
                logger.error(f"Secure storage deletion failed: {e}")
                # Fall through to manual deletion
        
        # Manual deletion fallback
        # Delete from database
        delete_result = await db_manager.db.processed_cards.delete_one({"_id": object_id})
        
        if delete_result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Record not found")
        
        # Try to delete associated files from static directory
        filename = record.get("filename", "")
        if filename:
            static_files = list(STATIC_DIR.glob(f"*{filename}*"))
            deleted_files = 0
            for file_path in static_files:
                try:
                    file_path.unlink()
                    deleted_files += 1
                except Exception as e:
                    logger.warning(f"Could not delete file {file_path}: {e}")
            
            if deleted_files > 0:
                logger.info(f"Deleted {deleted_files} associated files")
        
        logger.info(f"Successfully deleted record: {record_id}")
        return {
            "message": "Record and associated files deleted successfully",
            "record_id": record_id,
            "files_deleted": deleted_files if 'deleted_files' in locals() else 0
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting record: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete record: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=config.API_HOST, port=config.API_PORT) 
