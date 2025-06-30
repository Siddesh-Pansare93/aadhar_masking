// JavaScript file placeholder

// Use relative URLs since we're hosted from the same server
const API_BASE_URL = window.location.origin;
let selectedFiles = [];

// Global variables for records management
let currentPage = 1;
let currentSearch = '';
const pageSize = 10;

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

    // Load records if switching to records tab
    if (tabName === 'records') {
        loadRecords();
        loadStatistics();
    }
}

// File handling for single image
document.addEventListener('DOMContentLoaded', () => {
    const singleFileInput = document.getElementById('single-file');
    if (singleFileInput) {
        singleFileInput.addEventListener('change', function(e) {
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
    }

    // File handling for bulk images
    const bulkFilesInput = document.getElementById('bulk-files');
    if (bulkFilesInput) {
        bulkFilesInput.addEventListener('change', function(e) {
            const files = Array.from(e.target.files);
            addBulkFiles(files);
        });
    }

    // Add search on Enter key
    const searchInput = document.getElementById('search-input');
    if (searchInput) {
        searchInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                searchRecords();
            }
        });
    }

    // Initialize drag and drop
    setupDragAndDrop();
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
    const storeInDB = document.getElementById('single-store-checkbox').checked;
    
    if (!file) {
        alert('Please select an image file');
        return;
    }

    showProcessing('single');
    
    try {
        const formData = new FormData();
        formData.append('file', file);

        // Choose endpoint based on storage preference
        const endpoint = storeInDB 
            ? `${API_BASE_URL}/process-and-store-image`
            : `${API_BASE_URL}/process-image?store=${storeInDB}`;

        const response = await fetch(endpoint, {
            method: 'POST',
            body: formData , 
            headers :{
                'X-API-Key' : '22b0eeb767d3a9e450b0f187ffb6429d74a20c3ff8750a9c046ad62bcfa26a3e' 
            }   
        });

        if (response.ok) {
            const result = await response.json();
            displaySingleResult(result, storeInDB);
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

function displaySingleResult(result, stored = false) {
    const resultsDiv = document.getElementById('single-results');
    
    const storageInfo = stored && result.record_id 
        ? `<div class="detail-item">
            <div class="detail-label">💾 Database Record</div>
            <div class="detail-value">
                <span style="color: #28a745; font-weight: bold;">Stored</span><br>
                <small>ID: ${result.record_id}</small>
            </div>
        </div>`
        : stored 
        ? `<div class="detail-item">
            <div class="detail-label">💾 Database Storage</div>
            <div class="detail-value" style="color: #dc3545;">Failed</div>
        </div>`
        : '';
    
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
                ${storageInfo}
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
                ${result.record_id ? `
                <button class="btn" style="background: #17a2b8; margin-left: 10px;" onclick="viewStoredRecord('${result.record_id}')">
                    📋 View Record
                </button>
                ` : ''}
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
    // Extract filename from the imageUrl
    const urlParts = imageUrl.split('/');
    const staticFilename = urlParts[urlParts.length - 1];
    
    // Use the dedicated download endpoint instead of direct static URL
    const downloadUrl = `${API_BASE_URL}/download/${staticFilename}`;
    
    // Create a temporary anchor element
    const link = document.createElement('a');
    link.href = downloadUrl;
    link.download = `masked_${filename}`;
    link.style.display = 'none';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

// Records Management Functions

async function loadRecords(page = 1, search = '') {
    const loadingDiv = document.getElementById('records-loading');
    const containerDiv = document.getElementById('records-container');
    
    loadingDiv.classList.add('show');
    
    try {
        let url = `${API_BASE_URL}/list-records?page=${page}&page_size=${pageSize}`;
        if (search) {
            url += `&search=${encodeURIComponent(search)}`;
        }
        
        const response = await fetch(url);
        if (response.ok) {
            const data = await response.json();
            displayRecords(data);
            displayPagination(data);
            currentPage = page;
            currentSearch = search;
        } else {
            throw new Error(`Failed to load records: ${response.status}`);
        }
    } catch (error) {
        containerDiv.innerHTML = `
            <div class="error-message">
                <h4>❌ Error Loading Records</h4>
                <p>${error.message}</p>
            </div>
        `;
    } finally {
        loadingDiv.classList.remove('show');
    }
}

function displayRecords(data) {
    const container = document.getElementById('records-container');
    
    if (data.records.length === 0) {
        container.innerHTML = `
            <div style="text-align: center; padding: 40px; color: #666;">
                <h3>📂 No Records Found</h3>
                <p>No stored records match your criteria.</p>
            </div>
        `;
        return;
    }
    
    const tableHTML = `
        <table class="records-table">
            <thead>
                <tr>
                    <th>Filename</th>
                    <th>Consumer</th>
                    <th>Processing Time</th>
                    <th>File Size</th>
                    <th>Locations Found</th>
                    <th>Created At</th>
                    <th>Status</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody>
                ${data.records.map(record => `
                    <tr>
                        <td><strong>${record.filename}</strong></td>
                        <td>${record.consumer_name || 'Unknown'}</td>
                        <td>${record.processing_time ? record.processing_time.toFixed(2) + 's' : '-'}</td>
                        <td>${record.file_size ? formatFileSize(record.file_size) : '-'}</td>
                        <td>${record.locations_found || 0}</td>
                        <td>${new Date(record.created_at).toLocaleString()}</td>
                        <td>
                            <span style="
                                padding: 4px 8px; 
                                border-radius: 4px; 
                                background: ${record.status === 'completed' ? '#d4edda' : '#f8d7da'}; 
                                color: ${record.status === 'completed' ? '#155724' : '#721c24'};
                                font-size: 0.8em;
                            ">
                                ${record.status}
                            </span>
                        </td>
                        <td>
                            <div class="record-actions">
                                <button class="action-btn view" onclick="viewRecordDetails('${record.id}')">
                                    👁 View
                                </button>
                                <button class="action-btn download" onclick="downloadStoredImage('${record.id}', 'masked')">
                                    📥 Download
                                </button>
                                <button class="action-btn delete" onclick="deleteStoredRecord('${record.id}')">
                                    🗑 Delete
                                </button>
                            </div>
                        </td>
                    </tr>
                `).join('')}
            </tbody>
        </table>
    `;
    
    container.innerHTML = tableHTML;
}

function displayPagination(data) {
    const container = document.getElementById('pagination-container');
    
    if (data.total_pages <= 1) {
        container.innerHTML = '';
        return;
    }
    
    let paginationHTML = '<div class="pagination">';
    
    // Previous button
    if (data.page > 1) {
        paginationHTML += `<button onclick="loadRecords(${data.page - 1}, '${currentSearch}')">← Previous</button>`;
    }
    
    // Page numbers
    const startPage = Math.max(1, data.page - 2);
    const endPage = Math.min(data.total_pages, data.page + 2);
    
    for (let i = startPage; i <= endPage; i++) {
        const activeClass = i === data.page ? 'active' : '';
        paginationHTML += `<button class="${activeClass}" onclick="loadRecords(${i}, '${currentSearch}')">${i}</button>`;
    }
    
    // Next button
    if (data.page < data.total_pages) {
        paginationHTML += `<button onclick="loadRecords(${data.page + 1}, '${currentSearch}')">Next →</button>`;
    }
    
    paginationHTML += '</div>';
    
    // Add record count info
    paginationHTML += `
        <div style="text-align: center; margin-top: 10px; color: #666;">
            Showing ${((data.page - 1) * data.page_size) + 1} to ${Math.min(data.page * data.page_size, data.total_count)} 
            of ${data.total_count} records
        </div>
    `;
    
    container.innerHTML = paginationHTML;
}

async function searchRecords() {
    const searchInput = document.getElementById('search-input');
    const searchTerm = searchInput.value.trim();
    await loadRecords(1, searchTerm);
}

async function refreshRecords() {
    await loadRecords(currentPage, currentSearch);
}

async function viewRecordDetails(recordId) {
    try {
        const response = await fetch(`${API_BASE_URL}/get-record/${recordId}`);
        if (response.ok) {
            const record = await response.json();
            showRecordModal(record);
        } else {
            alert('Failed to load record details');
        }
    } catch (error) {
        alert('Error loading record details: ' + error.message);
    }
}

function showRecordModal(record) {
    const modalHTML = `
        <div class="record-detail-modal" id="record-modal">
            <div class="modal-content">
                <span class="close-modal" onclick="closeRecordModal()">×</span>
                <h2>📋 Record Details</h2>
                
                <div class="result-details" style="margin: 20px 0;">
                    <div class="detail-item">
                        <div class="detail-label">Filename</div>
                        <div class="detail-value">${record.filename}</div>
                    </div>
                    <div class="detail-item">
                        <div class="detail-label">UID Numbers</div>
                        <div class="detail-value">
                            ${record.uid_numbers ? record.uid_numbers.map(uid => `<span class="uid-number">${uid}</span>`).join('') : '<span style="color: #666; font-style: italic;">Protected/Encrypted</span>'}
                        </div>
                    </div>
                    <div class="detail-item">
                        <div class="detail-label">Created At</div>
                        <div class="detail-value">${new Date(record.created_at).toLocaleString()}</div>
                    </div>
                    <div class="detail-item">
                        <div class="detail-label">Status</div>
                        <div class="detail-value">${record.status}</div>
                    </div>
                </div>
                
                <div style="text-align: center;">
                    <button class="btn download-btn" onclick="downloadStoredImage('${record.id}', 'original')">
                        📥 Download Original
                    </button>
                    <button class="btn download-btn" onclick="downloadStoredImage('${record.id}', 'masked')">
                        📥 Download Masked
                    </button>
                    <button class="btn" style="background: #dc3545;" onclick="deleteStoredRecord('${record.id}')">
                        🗑 Delete Record
                    </button>
                </div>
            </div>
        </div>
    `;
    
    document.body.insertAdjacentHTML('beforeend', modalHTML);
    document.getElementById('record-modal').style.display = 'block';
}

function closeRecordModal() {
    const modal = document.getElementById('record-modal');
    if (modal) {
        modal.remove();
    }
}

async function downloadStoredImage(recordId, imageType) {
    try {
        const response = await fetch(`${API_BASE_URL}/retrieve-image/${recordId}/${imageType}`);
        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `${imageType}_${recordId}.png`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);
        } else {
            alert('Failed to download image');
        }
    } catch (error) {
        alert('Error downloading image: ' + error.message);
    }
}

async function deleteStoredRecord(recordId) {
    if (!confirm('Are you sure you want to delete this record? This action cannot be undone.')) {
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE_URL}/delete-record/${recordId}`, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            alert('Record deleted successfully');
            await loadRecords(currentPage, currentSearch);
            closeRecordModal();
        } else {
            const errorData = await response.json();
            alert('Failed to delete record: ' + errorData.detail);
        }
    } catch (error) {
        alert('Error deleting record: ' + error.message);
    }
}

async function loadStatistics() {
    try {
        const response = await fetch(`${API_BASE_URL}/statistics`);
        if (response.ok) {
            const stats = await response.json();
            displayStatistics(stats);
        }
    } catch (error) {
        console.error('Failed to load statistics:', error);
    }
}

function displayStatistics(stats) {
    const container = document.getElementById('statistics-container');
    
    const statsHTML = `
        <h3>📊 System Statistics</h3>
        <div class="statistics-grid">
            <div class="stat-card">
                <h4>Total Records</h4>
                <div class="stat-value">${stats.total_records || 0}</div>
            </div>
            <div class="stat-card">
                <h4>Recent Activity (24h)</h4>
                <div class="stat-value">${stats.recent_activity_24h || 0}</div>
            </div>
            <div class="stat-card">
                <h4>Database Size</h4>
                <div class="stat-value">${((stats.gridfs_size_bytes || 0) / 1024 / 1024).toFixed(1)} MB</div>
            </div>
            <div class="stat-card">
                <h4>Encryption Status</h4>
                <div class="stat-value" style="color: #28a745;">🔒 Active</div>
            </div>
        </div>
    `;
    
    container.innerHTML = statsHTML;
}

function viewStoredRecord(recordId) {
    // Switch to records tab and highlight the record
    switchTab('records');
    setTimeout(() => {
        viewRecordDetails(recordId);
    }, 500);
}

// Log API responses for debugging
window.addEventListener('load', () => {
    console.log('Enhanced Frontend loaded and ready!');
    console.log('API Base URL:', API_BASE_URL);
});


