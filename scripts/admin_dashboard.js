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
        .then(response => response ? response.json() : null)
        .then(data => {
            if (data) {
                const resultsDiv = document.getElementById('debug-results');
                resultsDiv.innerHTML = `
                    <h4>Debug Results</h4>
                    <p>Total API Keys: ${data.total_api_keys}</p>
                    <pre>${JSON.stringify(data, null, 2)}</pre>
                `;
            }
        })
        .catch(error => {
            console.error('Debug error:', error);
            showError('Debug operation failed');
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
    
    makeAuthenticatedRequest(`/admin/lookup-api-key-id/${encodeURIComponent(apiKey)}`)
        .then(response => response ? response.json() : null)
        .then(data => {
            if (data) {
                const resultsDiv = document.getElementById('lookup-results');
                resultsDiv.innerHTML = `
                    <div class="settings-card" style="margin-top: 1rem;">
                        <h4>Lookup Results</h4>
                        <div class="info-item">
                            <span>API Key ID:</span>
                            <span><code>${data.api_key_id}</code></span>
                        </div>
                        <div class="info-item">
                            <span>Consumer:</span>
                            <span>${data.consumer_name}</span>
                        </div>
                        <div class="info-item">
                            <span>Email:</span>
                            <span>${data.consumer_email}</span>
                        </div>
                        <div class="info-item">
                            <span>Status:</span>
                            <span class="status-badge ${data.is_active ? 'connected' : 'disconnected'}">
                                ${data.is_active ? 'Active' : 'Inactive'}
                            </span>
                        </div>
                    </div>
                `;
            }
        })
        .catch(error => {
            console.error('Lookup error:', error);
            showError('Lookup failed');
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
    
    makeAuthenticatedRequest(`/admin/debug/request-logs/${encodeURIComponent(identifier)}`)
        .then(response => response ? response.json() : null)
        .then(data => {
            if (data) {
                const resultsDiv = document.getElementById('logs-results');
                resultsDiv.innerHTML = `
                    <div class="settings-card" style="margin-top: 1rem;">
                        <h4>Request Logs</h4>
                        <p>Consumer: ${data.consumer_name}</p>
                        <p>Total Logs: ${data.request_logs_count}</p>
                        <pre style="max-height: 300px; overflow-y: auto;">${JSON.stringify(data.recent_logs, null, 2)}</pre>
                    </div>
                `;
            }
        })
        .catch(error => {
            console.error('Logs error:', error);
            showError('Failed to load logs');
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