"""
Authentication utilities and dependencies for the Aadhaar UID Masking API.
Provides API key authentication and admin authentication.
"""

import secrets
import base64
from typing import Optional, Dict, Any
from datetime import datetime
import logging

from fastapi import HTTPException, Depends, Request, Header
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from .api_key_manager import api_key_manager

logger = logging.getLogger(__name__)

# HTTP Basic Auth for admin endpoints
security = HTTPBasic()

# Admin credentials (in production, these should be from environment variables)
ADMIN_USERNAME = "admin123"
ADMIN_PASSWORD = "admin123"

async def get_api_key_from_header(x_api_key: Optional[str] = Header(None)) -> Optional[str]:
    """
    Extract API key from X-API-Key header.
    
    Args:
        x_api_key: API key from header
        
    Returns:
        Optional[str]: API key if present
    """
    return x_api_key

async def authenticate_api_key(
    request: Request,
    api_key: Optional[str] = Depends(get_api_key_from_header)
) -> Dict[str, Any]:
    """
    Dependency to authenticate API key from request headers.
    
    Args:
        request: FastAPI request object
        api_key: API key from header
        
    Returns:
        Dict: Authenticated consumer data
        
    Raises:
        HTTPException: If authentication fails
    """

    logger.debug(f"Authenticating API key: {api_key}")  
    if not api_key:
        raise HTTPException(
            status_code=401,
            detail="API key required. Please provide X-API-Key header.",
            headers={"WWW-Authenticate": "API-Key"}
        )
    
    # Authenticate the API key
    consumer_data = await api_key_manager.authenticate_api_key(api_key)
    
    if not consumer_data:
        raise HTTPException(
            status_code=401,
            detail="Invalid or inactive API key.",
            headers={"WWW-Authenticate": "API-Key"}
        )
    
    # Store consumer data in request state for later use
    request.state.consumer_data = consumer_data
    request.state.api_key = api_key
    
    logger.info(f"Authenticated request from {consumer_data['consumer_name']} ({consumer_data['consumer_email']})")
    
    return consumer_data

async def authenticate_admin(
    request: Request,
    admin_session: Optional[str] = Header(None, alias="X-Admin-Session"),
    credentials: Optional[HTTPBasicCredentials] = Depends(security)
) -> bool:
    """
    Dependency to authenticate admin users with session support and basic auth fallback.
    
    Args:
        request: FastAPI request object
        admin_session: Session token from header
        credentials: HTTP Basic Auth credentials (fallback)
        
    Returns:
        bool: True if authenticated
        
    Raises:
        HTTPException: If authentication fails
    """
    # First, try session authentication
    if admin_session:
        # Check if session_manager is available in the app state
        session_manager = getattr(request.app.state, 'session_manager', None)
        
        if session_manager:
            session_data = session_manager.verify_session(admin_session)
            if session_data:
                logger.info(f"Admin authenticated via session: {session_data['user_id']}")
                request.state.admin_user = session_data['user_id']
                request.state.admin_session = admin_session
                return True
            else:
                logger.warning(f"Invalid admin session token provided: {admin_session[:8]}...")
    
    # Fallback to basic auth for backward compatibility
    if credentials:
        # Constant-time comparison to prevent timing attacks
        correct_username = secrets.compare_digest(credentials.username, ADMIN_USERNAME)
        correct_password = secrets.compare_digest(credentials.password, ADMIN_PASSWORD)
        
        if correct_username and correct_password:
            logger.info(f"Admin authenticated via basic auth: {credentials.username}")
            request.state.admin_user = credentials.username
            return True
    
    # No valid authentication found
    raise HTTPException(
        status_code=401,
        detail="Admin authentication required. Please login or provide valid credentials.",
        headers={"WWW-Authenticate": "Basic"},
    )

async def log_api_request(
    request: Request,
    endpoint: str,
    processing_time: float,
    status: str,
    error_message: Optional[str] = None,
    file_size: Optional[int] = None,
    locations_found: Optional[int] = None
) -> None:
    """
    Log API request for analytics.
    
    Args:
        request: FastAPI request object
        endpoint: API endpoint called
        processing_time: Request processing time
        status: 'success' or 'failed'
        error_message: Error message if failed
        file_size: Size of processed file
        locations_found: Number of locations found
    """
    try:
        # Get consumer data from request state
        consumer_data = getattr(request.state, 'consumer_data', None)
        
        if consumer_data:
            await api_key_manager.log_request(
                api_key_id=consumer_data["_id"],
                endpoint=endpoint,
                processing_time=processing_time,
                status=status,
                error_message=error_message,
                file_size=file_size,
                locations_found=locations_found
            )
        
    except Exception as e:
        logger.error(f"Failed to log API request: {e}")

class AuthenticationMiddleware:
    """Middleware for handling authentication and logging."""
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            request = Request(scope, receive)
            
            # Skip authentication for certain paths
            skip_auth_paths = [
                "/",
                "/docs",
                "/openapi.json",
                "/redoc",
                "/health",
                "/api/info"
            ]
            
            path = request.url.path
            
            # Skip authentication for excluded paths
            if any(path.startswith(skip_path) for skip_path in skip_auth_paths):
                await self.app(scope, receive, send)
                return
            
            # For admin endpoints, authentication is handled by dependencies
            if path.startswith("/admin"):
                await self.app(scope, receive, send)
                return
            
            # For other endpoints, we'll handle authentication in the endpoint dependencies
            
        await self.app(scope, receive, send)
