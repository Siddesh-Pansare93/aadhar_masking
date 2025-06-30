// Admin Dashboard JavaScript Functions

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
function setupCreateKeyForm() {
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
}

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
                        <button class="btn" onclick="viewAnalytics('${key.id}')" style="margin-left: 5px;">Analytics</button>
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
            <div class="modal" id="analytics-modal">
                <div class="modal-content">
                    <span class="modal-close" onclick="closeAnalyticsModal()">×</span>
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
                                <div class="activity-item ${req.status === 'success' ? '' : 'failed'}">
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

// Initialize dashboard when page loads
document.addEventListener('DOMContentLoaded', function() {
    // Set up form handler
    setupCreateKeyForm();
    
    // Load overview data initially
    loadOverview();
});

// Load overview on page load (backup)
window.addEventListener('load', function() {
    loadOverview();
}); 