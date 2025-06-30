// Admin Login JavaScript

document.addEventListener('DOMContentLoaded', function() {
    const loginForm = document.getElementById('login-form');
    const loginBtn = document.getElementById('login-btn');
    const loginMessage = document.getElementById('login-message');
    const usernameInput = document.getElementById('username');
    const passwordInput = document.getElementById('password');
    const rememberCheckbox = document.getElementById('remember');

    // Check if user is already logged in
    checkExistingSession();

    // Form submission handler
    loginForm.addEventListener('submit', handleLogin);

    // Enter key handler for inputs
    usernameInput.addEventListener('keypress', handleEnterKey);
    passwordInput.addEventListener('keypress', handleEnterKey);

    // Auto-focus username field
    usernameInput.focus();
});

function handleEnterKey(event) {
    if (event.key === 'Enter') {
        event.preventDefault();
        handleLogin(event);
    }
}

async function handleLogin(event) {
    event.preventDefault();

    const username = document.getElementById('username').value.trim();
    const password = document.getElementById('password').value;
    const remember = document.getElementById('remember').checked;

    // Validation
    if (!username || !password) {
        showMessage('Please enter both username and password', 'error');
        return;
    }

    // Show loading state
    setLoadingState(true);
    clearMessage();

    try {
        const response = await fetch('/admin/login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                username: username,
                password: password,
                remember: remember
            })
        });

        const data = await response.json();

        if (response.ok) {
            showMessage('Login successful! Redirecting...', 'success');
            
            // Store session info if needed
            if (data.session_token) {
                if (remember) {
                    localStorage.setItem('admin_session', data.session_token);
                } else {
                    sessionStorage.setItem('admin_session', data.session_token);
                }
            }

            // Redirect after short delay
            setTimeout(() => {
                window.location.href = data.redirect_url || '/admin/dashboard';
            }, 1500);

        } else {
            showMessage(data.detail || 'Invalid credentials. Please try again.', 'error');
            
            // Clear password field on error
            document.getElementById('password').value = '';
            document.getElementById('password').focus();
        }

    } catch (error) {
        console.error('Login error:', error);
        showMessage('Network error. Please check your connection and try again.', 'error');
    } finally {
        setLoadingState(false);
    }
}

function setLoadingState(loading) {
    const loginBtn = document.getElementById('login-btn');
    const btnText = loginBtn.querySelector('.btn-text');
    const btnSpinner = loginBtn.querySelector('.btn-spinner');

    if (loading) {
        loginBtn.disabled = true;
        loginBtn.classList.add('loading');
        btnText.textContent = 'Signing In...';
        btnSpinner.style.display = 'inline-block';
    } else {
        loginBtn.disabled = false;
        loginBtn.classList.remove('loading');
        btnText.textContent = 'Sign In';
        btnSpinner.style.display = 'none';
    }
}

function showMessage(message, type) {
    const messageDiv = document.getElementById('login-message');
    messageDiv.textContent = message;
    messageDiv.className = `login-message ${type}`;
    
    // Auto-clear success messages
    if (type === 'success') {
        setTimeout(() => {
            clearMessage();
        }, 3000);
    }
}

function clearMessage() {
    const messageDiv = document.getElementById('login-message');
    messageDiv.textContent = '';
    messageDiv.className = 'login-message';
}

function togglePassword() {
    const passwordInput = document.getElementById('password');
    const passwordEye = document.getElementById('password-eye');

    if (passwordInput.type === 'password') {
        passwordInput.type = 'text';
        passwordEye.classList.remove('fa-eye');
        passwordEye.classList.add('fa-eye-slash');
    } else {
        passwordInput.type = 'password';
        passwordEye.classList.remove('fa-eye-slash');
        passwordEye.classList.add('fa-eye');
    }
}

async function checkExistingSession() {
    try {
        // Check for existing session
        const sessionToken = localStorage.getItem('admin_session') || 
                           sessionStorage.getItem('admin_session');
        
        if (sessionToken) {
            const response = await fetch('/admin/verify-session', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    session_token: sessionToken
                })
            });

            if (response.ok) {
                // Valid session found, redirect to dashboard
                showMessage('Session found. Redirecting to dashboard...', 'success');
                setTimeout(() => {
                    window.location.href = '/admin/dashboard';
                }, 1000);
            } else {
                // Invalid session, clear it
                localStorage.removeItem('admin_session');
                sessionStorage.removeItem('admin_session');
            }
        }
    } catch (error) {
        console.error('Session check error:', error);
        // Clear potentially corrupted session data
        localStorage.removeItem('admin_session');
        sessionStorage.removeItem('admin_session');
    }
}

// Add some visual feedback for better UX
document.addEventListener('DOMContentLoaded', function() {
    // Add subtle animations to form elements
    const inputs = document.querySelectorAll('input');
    inputs.forEach(input => {
        input.addEventListener('focus', function() {
            this.parentElement.style.transform = 'scale(1.02)';
        });

        input.addEventListener('blur', function() {
            this.parentElement.style.transform = 'scale(1)';
        });
    });

    // Add ripple effect to login button
    const loginBtn = document.getElementById('login-btn');
    loginBtn.addEventListener('click', function(e) {
        const ripple = document.createElement('span');
        const rect = this.getBoundingClientRect();
        const size = Math.max(rect.width, rect.height);
        const x = e.clientX - rect.left - size / 2;
        const y = e.clientY - rect.top - size / 2;
        
        ripple.style.width = ripple.style.height = size + 'px';
        ripple.style.left = x + 'px';
        ripple.style.top = y + 'px';
        ripple.classList.add('ripple');
        
        this.appendChild(ripple);
        
        setTimeout(() => {
            ripple.remove();
        }, 600);
    });
});

// Add ripple effect CSS dynamically
const style = document.createElement('style');
style.textContent = `
    .login-btn {
        position: relative;
        overflow: hidden;
    }
    
    .ripple {
        position: absolute;
        border-radius: 50%;
        background: rgba(255, 255, 255, 0.3);
        transform: scale(0);
        animation: ripple 0.6s linear;
        pointer-events: none;
    }
    
    @keyframes ripple {
        to {
            transform: scale(2);
            opacity: 0;
        }
    }
    
    .input-wrapper {
        transition: transform 0.2s ease;
    }
`;
document.head.appendChild(style); 