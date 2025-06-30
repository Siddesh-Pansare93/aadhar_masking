"""
Configuration management for the Aadhaar UID Masking system.
Handles environment variables and application settings.
"""

import os
from typing import List, Optional
from pathlib import Path
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import secrets

# Load environment variables
from dotenv import load_dotenv
# .env is outside the src folder(../)
    
load_dotenv(dotenv_path=Path(__file__).parent.parent / '.env')

class Config:
    """Application configuration class."""
    
    # Database Configuration
    MONGODB_URL: str = os.getenv("MONGODB_URL", "mongodb+srv://siddeshpansare93:Siddesh207@cluster0.hpvnyoh.mongodb.net/?retryWrites=true&w=majority&appName=cluster0")
    DATABASE_NAME: str = os.getenv("DATABASE_NAME", "aadhaar_masking_db")
    GRID_FS_BUCKET: str = os.getenv("GRID_FS_BUCKET", "encrypted_images")
    
    # Encryption Configuration
    ENCRYPTION_KEY: str = os.getenv("ENCRYPTION_KEY", "")
    SALT_KEY: str = os.getenv("SALT_KEY", "devionx")
    
    # API Configuration
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    
    # File Storage Configuration
    MAX_FILE_SIZE_MB: int = int(os.getenv("MAX_FILE_SIZE_MB", "10"))
    MAX_BULK_FILES: int = int(os.getenv("MAX_BULK_FILES", "10"))
    CLEANUP_INTERVAL_HOURS: int = int(os.getenv("CLEANUP_INTERVAL_HOURS", "24"))
    
    # Security Configuration
    SESSION_SECRET: str = os.getenv("SESSION_SECRET", "your_session_secret_here")
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000", 
        "http://localhost:8000",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8000"
    ]
    
    # Directory paths
    BASE_DIR = Path(__file__).parent.parent
    UPLOAD_DIR = BASE_DIR / "uploads"
    OUTPUT_DIR = BASE_DIR / "output" 
    STATIC_DIR = BASE_DIR / "static"
    
    @classmethod
    def validate_config(cls) -> None:
        """Validate that all required configuration is present."""
        if not cls.ENCRYPTION_KEY:
            raise ValueError("ENCRYPTION_KEY environment variable is required")
        
        if not cls.SALT_KEY:
            raise ValueError("SALT_KEY environment variable is required")
    
    @classmethod
    def generate_keys(cls) -> tuple[str, str]:
        """Generate secure encryption and salt keys for development."""
        # Generate encryption key
        encryption_key = Fernet.generate_key().decode()
        
        # Generate salt key
        salt_key = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode()
        
        return encryption_key, salt_key
    
    @classmethod
    def setup_development_keys(cls) -> None:
        """Set up development keys if they don't exist."""
        if not cls.ENCRYPTION_KEY or cls.ENCRYPTION_KEY == "your_secret_encryption_key_here":
            encryption_key, salt_key = cls.generate_keys()
            cls.ENCRYPTION_KEY = encryption_key
            cls.SALT_KEY = salt_key
            print("⚠️  Development keys generated. In production, set proper environment variables:")
            print(f"ENCRYPTION_KEY={encryption_key}")
            print(f"SALT_KEY={salt_key}")
    
    @classmethod
    def get_fernet_key(cls) -> bytes:
        """Get or derive the Fernet encryption key."""
        if not cls.ENCRYPTION_KEY:
            raise ValueError("No encryption key available")
        
        try:
            # Try to use the key directly if it's a valid base64-encoded Fernet key
            key_bytes = cls.ENCRYPTION_KEY.encode('utf-8')
            # Test if it's a valid Fernet key by trying to decode it
            test_key = base64.urlsafe_b64decode(key_bytes)
            if len(test_key) == 32:
                return key_bytes
            else:
                # If not 32 bytes, derive a proper key
                return cls._derive_key_from_password(cls.ENCRYPTION_KEY)
        except Exception:
            # If decoding fails, derive key using PBKDF2
            return cls._derive_key_from_password(cls.ENCRYPTION_KEY)
    
    @classmethod
    def _derive_key_from_password(cls, password: str) -> bytes:
        """Derive a Fernet key from a password using PBKDF2."""
        salt = cls.SALT_KEY.encode() if cls.SALT_KEY else b"default_salt_change_in_production"
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key

# Global config instance
config = Config()

# Environment setup for development
if config.ENVIRONMENT == "development":
    config.setup_development_keys() 