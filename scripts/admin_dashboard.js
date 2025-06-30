// Enhanced Admin Dashboard JavaScript

// Global variables
let currentSessionToken = null;

document.addEventListener('DOMContentLoaded', function() {
    // Check session and initialize dashboard
    checkAdminSession();
    
    // Initialize dashboard
    showSection('overview');
    
    // Set up form handlers
    setupFormHandlers();
    
    // Set up periodic refresh
    setInterval(refreshCurrentSection, 30000); // Refresh every 30 seconds
});

// Session Management
async function checkAdminSession() {
    try {
        const sessionToken = localStorage.getItem('admin_session') || 
                           sessionStorage.getItem('admin_session');
        
        if (sessionToken) {
            currentSessionToken = sessionToken;
            
            // Verify session with server
            const response = await fetch('/admin/verify-session', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    session_token: sessionToken
                })
            });

            const data = await response.json();
            
            if (!data.valid) {
                // Session invalid, redirect to login
                localStorage.removeItem('admin_session');
                sessionStorage.removeItem('admin_session');
                window.location.href = '/admin/login';
                return;
            }
            
            // Update UI to show logged in state
            const adminUsername = document.getElementById('admin-username');
            if (adminUsername) {
                adminUsername.textContent = 'Administrator';
            }
        } else {
            // No session found, redirect to login
            window.location.href = '/admin/login';
            return;
        }
    } catch (error) {
        console.error('Session check error:', error);
        // On error, redirect to login
        window.location.href = '/admin/login';
    }
}

// Enhanced API Request Function
async function makeAuthenticatedRequest(url, options = {}) {
    if (!currentSessionToken) {
        window.location.href = '/admin/login';
        return null;
    }
    
    const defaultHeaders = {
        'Content-Type': 'application/json',
        'X-Admin-Session': currentSessionToken
    };
    
    const config = {
        ...options,
        headers: {
            ...defaultHeaders,
            ...options.headers
        }
    };
    
    try {
        const response = await fetch(url, config);
        
        if (response.status === 401) {
            // Session expired, redirect to login
            localStorage.removeItem('admin_session');
            sessionStorage.removeItem('admin_session');
            window.location.href = '/admin/login';
            return null;
        }
        
        return response;
    } catch (error) {
        console.error('Request error:', error);
        throw error;
    }
}

// Logout Functions
async function adminLogout() {
    const logoutModal = document.getElementById('logout-modal');
    if (logoutModal) {
        logoutModal.style.display = 'block';
    }
}

function closeLogoutModal() {
    const logoutModal = document.getElementById('logout-modal');
    if (logoutModal) {
        logoutModal.style.display = 'none';
    }
}

async function confirmLogout() {
    try {
        if (currentSessionToken) {
            await makeAuthenticatedRequest('/admin/logout', {
                method: 'POST',
                body: JSON.stringify({
                    session_token: currentSessionToken
                })
            });
        }
        
        // Clear session storage
        localStorage.removeItem('admin_session');
        sessionStorage.removeItem('admin_session');
        currentSessionToken = null;
        
        // Redirect to login
        window.location.href = '/admin/login';
        
    } catch (error) {
        console.error('Logout error:', error);
        // Even on error, clear session and redirect
        localStorage.removeItem('admin_session');
        sessionStorage.removeItem('admin_session');
        window.location.href = '/admin/login';
    }
}

// Section Management
function showSection(sectionName) {
    // Hide all sections
    const sections = document.querySelectorAll('.admin-section');
    sections.forEach(section => section.classList.remove('active'));
    
    // Show selected section
    const targetSection = document.getElementById(sectionName);
    if (targetSection) {
        targetSection.classList.add('active');
    }
    
    // Update nav buttons
    const navButtons = document.querySelectorAll('.nav-btn');
    navButtons.forEach(button => button.classList.remove('active'));
    
    // Find and activate the corresponding nav button
    const activeButton = document.querySelector(`[data-section="${sectionName}"]`);
    if (activeButton) {
        activeButton.classList.add('active');
    }
    
    // Load section-specific data
    switch(sectionName) {
        case 'overview':
            loadOverviewData();
            break;
        case 'api-keys':
            loadAPIKeys();
            break;
        case 'analytics':
            loadAnalytics();
            break;
        case 'settings':
            loadSystemInfo();
            break;
    }
}

function refreshCurrentSection() {
    const activeSection = document.querySelector('.admin-section.active');
    if (activeSection) {
        const sectionId = activeSection.id;
        switch(sectionId) {
            case 'overview':
                loadOverviewData();
                break;
            case 'api-keys':
                loadAPIKeys();
                break;
            case 'analytics':
                loadAnalytics();
                break;
        }
    }
}

function refreshOverview() {
    loadOverviewData();
}

// Overview Section
async function loadOverviewData() {
    try {
        const response = await makeAuthenticatedRequest('/admin/analytics');
        
        if (!response) return;
        
        const data = await response.json();
        
        // Update overview cards
        document.getElementById('total-api-keys').textContent = data.total_api_keys || 0;
        document.getElementById('total-requests').textContent = data.total_requests || 0;
        document.getElementById('success-rate').textContent = (data.success_rate || 0) + '%';
        document.getElementById('avg-processing-time').textContent = (data.average_processing_time || 0) + 's';
        
        // Load recent activity
        loadRecentActivity();
        
    } catch (error) {
        console.error('Error loading overview:', error);
        showError('Failed to load overview data');
    }
}

async function loadRecentActivity() {
    try {
        // This would be replaced with actual recent activity endpoint
        const activityContainer = document.getElementById('recent-activity-list');
        
        if (activityContainer) {
            activityContainer.innerHTML = `
                <div class="activity-item">
                    <div>
                        <strong>API Key Created</strong>
                        <br><small>New consumer registered - 2 minutes ago</small>
                    </div>
                    <span class="status-badge connected">Success</span>
                </div>
                <div class="activity-item">
                    <div>
                        <strong>Image Processed</strong>
                        <br><small>Bulk processing completed - 5 minutes ago</small>
                    </div>
                    <span class="status-badge connected">Success</span>
                </div>
                <div class="activity-item">
                    <div>
                        <strong>System Health Check</strong>
                        <br><small>All systems operational - 10 minutes ago</small>
                    </div>
                    <span class="status-badge connected">Success</span>
                </div>
            `;
        }
    } catch (error) {
        console.error('Error loading recent activity:', error);
    }
}

// API Keys Section
async function loadAPIKeys() {
    try {
        const container = document.getElementById('keys-container');
        const loading = document.getElementById('keys-loading');
        
        if (loading) loading.style.display = 'block';
        
        const response = await makeAuthenticatedRequest('/admin/api-keys?include_inactive=true');
        
        if (!response) return;
        
        const data = await response.json();
        
        if (loading) loading.style.display = 'none';
        
        if (data.api_keys && data.api_keys.length > 0) {
            let html = '';
            
            data.api_keys.forEach(key => {
                html += `
                    <div class="api-key-item">
                        <div class="key-info">
                            <h4>${key.consumer_name}</h4>
                            <p>${key.consumer_email}</p>
                            <p><small>Created: ${new Date(key.created_at).toLocaleDateString()}</small></p>
                            <p><small>Requests: ${key.total_requests} (${key.successful_requests} success, ${key.failed_requests} failed)</small></p>
                        </div>
                        <div class="key-actions">
                            <span class="status-badge ${key.is_active ? 'connected' : 'disconnected'}">
                                ${key.is_active ? 'Active' : 'Inactive'}
                            </span>
                            ${key.is_active ? 
                                `<button class="btn btn-danger" onclick="deactivateKey('${key.id}')">
                                    <i class="fas fa-pause"></i> Deactivate
                                </button>` :
                                `<button class="btn btn-secondary" onclick="activateKey('${key.id}')">
                                    <i class="fas fa-play"></i> Activate
                                </button>`
                            }
                            <button class="btn btn-secondary" onclick="viewAnalytics('${key.id}')">
                                <i class="fas fa-chart-bar"></i> Analytics
                            </button>
                        </div>
                    </div>
                `;
            });
            
            container.innerHTML = html;
        } else {
            container.innerHTML = `
                <div class="loading">
                    <i class="fas fa-info-circle"></i>
                    No API keys found. Create your first API key to get started.
                </div>
            `;
        }
    } catch (error) {
        console.error('Error loading API keys:', error);
        showError('Failed to load API keys');
    }
}

// API Key Actions
async function deactivateKey(keyId) {
    if (confirm('Are you sure you want to deactivate this API key?')) {
        try {
            const response = await makeAuthenticatedRequest(`/admin/api-keys/${keyId}/deactivate`, {
                method: 'POST'
            });
            
            if (response && response.ok) {
                showSuccess('API key deactivated successfully');
                loadAPIKeys();
            } else {
                showError('Failed to deactivate API key');
            }
        } catch (error) {
            console.error('Error deactivating key:', error);
            showError('Error deactivating API key');
        }
    }
}

async function activateKey(keyId) {
    try {
        const response = await makeAuthenticatedRequest(`/admin/api-keys/${keyId}/activate`, {
            method: 'POST'
        });
        
        if (response && response.ok) {
            showSuccess('API key activated successfully');
            loadAPIKeys();
        } else {
            showError('Failed to activate API key');
        }
    } catch (error) {
        console.error('Error activating key:', error);
        showError('Error activating API key');
    }
}

async function viewAnalytics(keyId) {
    try {
        const response = await makeAuthenticatedRequest(`/admin/api-keys/${keyId}/analytics`);
        
        if (!response || !response.ok) {
            throw new Error('Failed to fetch analytics');
        }
        
        const data = await response.json();
        
        // Show analytics in a more detailed way
        alert(`Analytics for ${data.consumer_name}:\n\n` +
              `Total Requests: ${data.total_requests}\n` +
              `Success Rate: ${data.success_rate}%\n` +
              `Average Processing Time: ${data.average_processing_time}s\n` +
              `Last Used: ${data.last_used || 'Never'}`);
        
    } catch (error) {
        console.error('Error loading analytics:', error);
        showError('Failed to load analytics');
    }
}

// Analytics Section
async function loadAnalytics() {
    try {
        const container = document.getElementById('analytics-container');
        const loading = document.getElementById('analytics-loading');
        
        if (loading) loading.style.display = 'block';
        
        const response = await makeAuthenticatedRequest('/admin/analytics');
        
        if (!response) return;
        
        const data = await response.json();
        
        if (loading) loading.style.display = 'none';
        
        let html = `
            <div class="overview-grid">
                <div class="overview-card">
                    <div class="card-icon"><i class="fas fa-calendar-day"></i></div>
                    <div class="card-content">
                        <h3>${data.requests_today || 0}</h3>
                        <p>Requests Today</p>
                    </div>
                </div>
                <div class="overview-card">
                    <div class="card-icon"><i class="fas fa-calendar-week"></i></div>
                    <div class="card-content">
                        <h3>${data.requests_this_week || 0}</h3>
                        <p>Requests This Week</p>
                    </div>
                </div>
                <div class="overview-card">
                    <div class="card-icon"><i class="fas fa-calendar-alt"></i></div>
                    <div class="card-content">
                        <h3>${data.requests_this_month || 0}</h3>
                        <p>Requests This Month</p>
                    </div>
                </div>
                <div class="overview-card">
                    <div class="card-icon"><i class="fas fa-clock"></i></div>
                    <div class="card-content">
                        <h3>${data.average_processing_time || 0}s</h3>
                        <p>Avg Processing Time</p>
                    </div>
                </div>
            </div>
            
            <div class="settings-card" style="margin-top: 2rem;">
                <h4><i class="fas fa-chart-bar"></i> System Statistics</h4>
                <div class="info-item">
                    <span>Total API Keys:</span>
                    <span>${data.total_api_keys || 0}</span>
                </div>
                <div class="info-item">
                    <span>Active API Keys:</span>
                    <span>${data.active_api_keys || 0}</span>
                </div>
                <div class="info-item">
                    <span>Total Requests:</span>
                    <span>${data.total_requests || 0}</span>
                </div>
                <div class="info-item">
                    <span>Successful Requests:</span>
                    <span>${data.successful_requests || 0}</span>
                </div>
                <div class="info-item">
                    <span>Failed Requests:</span>
                    <span>${data.failed_requests || 0}</span>
                </div>
                <div class="info-item">
                    <span>Success Rate:</span>
                    <span>${data.success_rate || 0}%</span>
                </div>
                <div class="info-item">
                    <span>Last Updated:</span>
                    <span>${new Date(data.last_updated || Date.now()).toLocaleString()}</span>
                </div>
            </div>
        `;
        
        container.innerHTML = html;
    } catch (error) {
        console.error('Error loading analytics:', error);
        showError('Failed to load analytics');
    }
}

function refreshAnalytics() {
    loadAnalytics();
}

// Settings Section
async function loadSystemInfo() {
    try {
        const response = await makeAuthenticatedRequest('/health');
        
        if (response && response.ok) {
            const data = await response.json();
            
            // Update system status indicators
            const dbStatus = document.getElementById('db-status');
            const encryptionStatus = document.getElementById('encryption-status');
            
            if (dbStatus) {
                dbStatus.textContent = data.database_connected ? 'Connected' : 'Disconnected';
                dbStatus.className = `status-badge ${data.database_connected ? 'connected' : 'disconnected'}`;
            }
            
            if (encryptionStatus) {
                encryptionStatus.textContent = data.encryption_ready ? 'Ready' : 'Error';
                encryptionStatus.className = `status-badge ${data.encryption_ready ? 'connected' : 'disconnected'}`;
            }
        }
    } catch (error) {
        console.error('Error loading system info:', error);
    }
}

// Modal Functions
function showCreateKeyModal() {
    const modal = document.getElementById('create-key-modal');
    if (modal) {
        modal.style.display = 'block';
    }
}

function closeCreateKeyModal() {
    const modal = document.getElementById('create-key-modal');
    if (modal) {
        modal.style.display = 'none';
    }
}

// Debug Tools
function debugApiKeys() {
    makeAuthenticatedRequest('/admin/debug/api-keys')
        .then(response => {
            if (!response) {
                throw new Error('No response received');
            }
            
            if (!response.ok) {
                return response.json().then(err => {
                    throw new Error(err.detail || `HTTP ${response.status}: ${response.statusText}`);
                });
            }
            
            return response.json();
        })
        .then(data => {
            const resultsDiv = document.getElementById('debug-results');
            
            let apiKeysDisplay = '';
            if (data.api_keys && data.api_keys.length > 0) {
                apiKeysDisplay = data.api_keys.map(key => `
                    <div style="background: #f8f9fa; padding: 15px; margin: 10px 0; border-radius: 8px; border-left: 4px solid ${key.is_active ? '#28a745' : '#dc3545'};">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                            <div style="font-weight: 600; color: #333;">${key.consumer_name || 'Unknown'}</div>
                            <span style="background: ${key.is_active ? '#28a745' : '#dc3545'}; color: white; padding: 2px 8px; border-radius: 12px; font-size: 0.8em;">
                                ${key.is_active ? 'Active' : 'Inactive'}
                            </span>
                        </div>
                        <div style="color: #666; font-size: 0.9em;">
                            <div>Email: ${key.consumer_email || 'Unknown'}</div>
                            <div>ID: <code>${key.id}</code></div>
                            <div>Created: ${key.created_at ? new Date(key.created_at).toLocaleString() : 'Unknown'}</div>
                            <div>Requests: ${key.total_requests || 0} (${key.successful_requests || 0} success, ${key.failed_requests || 0} failed)</div>
                        </div>
                    </div>
                `).join('');
            } else {
                apiKeysDisplay = '<div style="text-align: center; color: #666; padding: 20px;">No API keys found</div>';
            }
            
            resultsDiv.innerHTML = `
                <div class="settings-card">
                    <h4><i class="fas fa-search"></i> Debug Results - API Keys</h4>
                    <div class="info-item">
                        <span>Total API Keys:</span>
                        <span style="font-weight: 600; color: #667eea;">${data.total_api_keys || 0}</span>
                    </div>
                    
                    <h5 style="margin: 20px 0 10px 0;"><i class="fas fa-list"></i> API Keys Details</h5>
                    <div style="max-height: 500px; overflow-y: auto; border: 1px solid #e2e8f0; border-radius: 6px; padding: 10px;">
                        ${apiKeysDisplay}
                    </div>
                    
                    <details style="margin-top: 15px;">
                        <summary style="cursor: pointer; font-weight: 600; color: #667eea;">
                            <i class="fas fa-code"></i> Raw JSON Data
                        </summary>
                        <pre style="background: #f8f9fa; padding: 15px; border-radius: 6px; overflow-x: auto; margin-top: 10px; border: 1px solid #e2e8f0; font-size: 0.85em;">${JSON.stringify(data, null, 2)}</pre>
                    </details>
                </div>
            `;
        })
        .catch(error => {
            console.error('Debug error:', error);
            const resultsDiv = document.getElementById('debug-results');
            resultsDiv.innerHTML = `
                <div class="settings-card" style="border-left: 4px solid #ef4444;">
                    <h4><i class="fas fa-exclamation-triangle"></i> Debug Operation Failed</h4>
                    <p style="color: #ef4444; margin: 0;">${error.message}</p>
                    <p style="color: #64748b; margin: 10px 0 0 0; font-size: 0.9em;">
                        Please check your admin permissions and try again.
                    </p>
                </div>
            `;
        });
}

function showLookupTool() {
    const modal = document.getElementById('lookup-modal');
    if (modal) {
        modal.style.display = 'block';
    }
}

function closeLookupModal() {
    const modal = document.getElementById('lookup-modal');
    if (modal) {
        modal.style.display = 'none';
    }
}

function lookupApiKey() {
    const apiKey = document.getElementById('lookup-key').value.trim();
    
    if (!apiKey) {
        showError('Please enter an API key');
        return;
    }
    
    if (apiKey.length !== 64) {
        showError('API key must be exactly 64 characters');
        return;
    }
    
    makeAuthenticatedRequest(`/admin/lookup-api-key-id/${encodeURIComponent(apiKey)}`)
        .then(response => {
            if (!response) {
                throw new Error('No response received');
            }
            
            if (!response.ok) {
                return response.json().then(err => {
                    throw new Error(err.detail || `HTTP ${response.status}: ${response.statusText}`);
                });
            }
            
            return response.json();
        })
        .then(data => {
            const resultsDiv = document.getElementById('lookup-results');
            resultsDiv.innerHTML = `
                <div class="settings-card" style="margin-top: 1rem;">
                    <h4><i class="fas fa-search-plus"></i> Lookup Results</h4>
                    <div class="info-item">
                        <span>API Key ID:</span>
                        <span><code>${data.api_key_id || 'Not found'}</code></span>
                    </div>
                    <div class="info-item">
                        <span>Consumer:</span>
                        <span>${data.consumer_name || 'Unknown'}</span>
                    </div>
                    <div class="info-item">
                        <span>Email:</span>
                        <span>${data.consumer_email || 'Unknown'}</span>
                    </div>
                    <div class="info-item">
                        <span>Status:</span>
                        <span class="status-badge ${data.is_active ? 'connected' : 'disconnected'}">
                            ${data.is_active ? 'Active' : 'Inactive'}
                        </span>
                    </div>
                    <div class="info-item">
                        <span>Created:</span>
                        <span>${data.created_at ? new Date(data.created_at).toLocaleString() : 'Unknown'}</span>
                    </div>
                </div>
            `;
        })
        .catch(error => {
            console.error('Lookup error:', error);
            const resultsDiv = document.getElementById('lookup-results');
            resultsDiv.innerHTML = `
                <div class="settings-card" style="margin-top: 1rem; border-left: 4px solid #ef4444;">
                    <h4><i class="fas fa-exclamation-triangle"></i> Lookup Failed</h4>
                    <p style="color: #ef4444; margin: 0;">${error.message}</p>
                    <p style="color: #64748b; margin: 10px 0 0 0; font-size: 0.9em;">
                        Please check the API key format and try again.
                    </p>
                </div>
            `;
        });
}

function showLogsTool() {
    const modal = document.getElementById('logs-modal');
    if (modal) {
        modal.style.display = 'block';
    }
}

function closeLogsModal() {
    const modal = document.getElementById('logs-modal');
    if (modal) {
        modal.style.display = 'none';
    }
}

function viewRequestLogs() {
    const identifier = document.getElementById('logs-identifier').value.trim();
    
    if (!identifier) {
        showError('Please enter an API key or API key ID');
        return;
    }
    
    // Validate input
    if (identifier.length !== 64 && identifier.length !== 24) {
        showError('Please enter a valid API key (64 chars) or API key ID (24 chars)');
        return;
    }
    
    makeAuthenticatedRequest(`/admin/debug/request-logs/${encodeURIComponent(identifier)}`)
        .then(response => {
            if (!response) {
                throw new Error('No response received');
            }
            
            if (!response.ok) {
                return response.json().then(err => {
                    throw new Error(err.detail || `HTTP ${response.status}: ${response.statusText}`);
                });
            }
            
            return response.json();
        })
        .then(data => {
            const resultsDiv = document.getElementById('logs-results');
            
            // Format recent logs for better display
            let logsDisplay = '';
            if (data.recent_logs && data.recent_logs.length > 0) {
                logsDisplay = data.recent_logs.map(log => `
                    <div style="background: #f8f9fa; padding: 12px; margin: 8px 0; border-radius: 6px; border-left: 3px solid ${log.status === 'success' ? '#28a745' : '#dc3545'};">
                        <div style="font-weight: 600; color: #333;">${log.endpoint || 'Unknown endpoint'}</div>
                        <div style="color: #666; font-size: 0.9em;">
                            Status: <span style="color: ${log.status === 'success' ? '#28a745' : '#dc3545'};">${log.status || 'unknown'}</span> | 
                            Time: ${log.timestamp ? new Date(log.timestamp).toLocaleString() : 'Unknown'} | 
                            Processing: ${log.processing_time || 0}s
                        </div>
                        ${log.error_message ? `<div style="color: #dc3545; font-size: 0.85em; margin-top: 4px;">Error: ${log.error_message}</div>` : ''}
                    </div>
                `).join('');
            } else {
                logsDisplay = '<div style="text-align: center; color: #666; padding: 20px;">No recent logs found</div>';
            }
            
            resultsDiv.innerHTML = `
                <div class="settings-card" style="margin-top: 1rem;">
                    <h4><i class="fas fa-file-alt"></i> Request Logs</h4>
                    <div class="info-item">
                        <span>Consumer:</span>
                        <span>${data.consumer_name || 'Unknown'}</span>
                    </div>
                    <div class="info-item">
                        <span>API Key ID:</span>
                        <span><code>${data.api_key_id || 'Unknown'}</code></span>
                    </div>
                    <div class="info-item">
                        <span>Total Logs:</span>
                        <span>${data.request_logs_count || 0}</span>
                    </div>
                    <div class="info-item">
                        <span>Total Requests:</span>
                        <span>${data.api_key_stats?.total_requests || 0}</span>
                    </div>
                    <div class="info-item">
                        <span>Success Rate:</span>
                        <span style="color: ${(data.api_key_stats?.total_requests || 0) > 0 ? '#28a745' : '#666'};">
                            ${data.api_key_stats?.total_requests > 0 ? 
                                Math.round((data.api_key_stats.successful_requests / data.api_key_stats.total_requests) * 100) + '%' : 
                                'N/A'
                            }
                        </span>
                    </div>
                    
                    <h5 style="margin: 20px 0 10px 0;"><i class="fas fa-history"></i> Recent Activity</h5>
                    <div style="max-height: 400px; overflow-y: auto; border: 1px solid #e2e8f0; border-radius: 6px; padding: 10px;">
                        ${logsDisplay}
                    </div>
                </div>
            `;
        })
        .catch(error => {
            console.error('Logs error:', error);
            const resultsDiv = document.getElementById('logs-results');
            resultsDiv.innerHTML = `
                <div class="settings-card" style="margin-top: 1rem; border-left: 4px solid #ef4444;">
                    <h4><i class="fas fa-exclamation-triangle"></i> Failed to Load Logs</h4>
                    <p style="color: #ef4444; margin: 0;">${error.message}</p>
                    <p style="color: #64748b; margin: 10px 0 0 0; font-size: 0.9em;">
                        Please check the API key/ID format and try again.
                    </p>
                </div>
            `;
        });
}

// Form Handlers
function setupFormHandlers() {
    const createKeyForm = document.getElementById('create-key-form');
    if (createKeyForm) {
        createKeyForm.addEventListener('submit', handleCreateKey);
    }
}

async function handleCreateKey(event) {
    event.preventDefault();
    
    const formData = new FormData(event.target);
    const data = {
        consumer_name: formData.get('consumer-name') || document.getElementById('consumer-name').value,
        consumer_email: formData.get('consumer-email') || document.getElementById('consumer-email').value,
        description: formData.get('description') || document.getElementById('description').value
    };
    
    try {
        const response = await makeAuthenticatedRequest('/admin/api-keys', {
            method: 'POST',
            body: JSON.stringify(data)
        });
        
        if (!response) return;
        
        const result = await response.json();
        
        if (response.ok) {
            showSuccess(`API Key created successfully for ${result.consumer_name}`);
            alert(`API Key: ${result.api_key}\n\nSave this key securely. It will not be shown again!`);
            closeCreateKeyModal();
            event.target.reset();
            loadAPIKeys();
        } else {
            showError(result.detail || 'Failed to create API key');
        }
    } catch (error) {
        console.error('Error creating API key:', error);
        showError('Error creating API key');
    }
}

// Utility Functions
function showError(message) {
    // Simple error display - could be enhanced with toast notifications
    alert('Error: ' + message);
}

function showSuccess(message) {
    // Simple success display - could be enhanced with toast notifications
    alert('Success: ' + message);
}

// Close modals when clicking outside
window.addEventListener('click', function(event) {
    const modals = document.querySelectorAll('.modal');
    modals.forEach(modal => {
        if (event.target === modal) {
            modal.style.display = 'none';
        }
    });
}); 