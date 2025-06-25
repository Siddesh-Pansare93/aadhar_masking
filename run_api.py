#!/usr/bin/env python3
"""
Startup script for the Aadhaar UID Masking API server.
"""

import uvicorn
import os

if __name__ == "__main__":
    # Configure server settings
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8000))
    reload = os.getenv("RELOAD", "True").lower() == "true"
    
    print("🚀 Starting Aadhaar UID Masking API Server...")
    print(f"📍 Frontend Application: http://{host}:{port}")
    print(f"📖 API Documentation: http://{host}:{port}/docs")
    print(f"ℹ️  API Info Endpoint: http://{host}:{port}/api/info")
    print(f"🔧 Reload mode: {reload}")
    
    uvicorn.run(
        "api:app",
        host=host,
        port=port,
        reload=reload,
        access_log=True,
        log_level="info"
    ) 