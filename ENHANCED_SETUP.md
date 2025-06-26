# Enhanced Aadhaar UID Masking System Setup Guide

## 🚀 Overview

This enhanced version of the Aadhaar UID Masking system includes:

- **Secure Database Storage**: MongoDB with GridFS for encrypted file storage
- **End-to-End Encryption**: AES encryption for images and UIDs using Fernet
- **Enhanced API**: New endpoints for storage, retrieval, and record management
- **Improved Frontend**: Records management interface with search and pagination
- **Security Features**: Proper key management and secure data handling

## 📋 Prerequisites

### Required Software
- Python 3.8 or higher
- MongoDB 4.4 or higher
- Git

### System Requirements
- RAM: Minimum 4GB (8GB recommended)
- Storage: At least 2GB free space
- Network: Internet connection for dependency installation

## 🛠️ Installation Steps

### 1. Install MongoDB

#### On Ubuntu/Debian:
```bash
# Import the public key
wget -qO - https://www.mongodb.org/static/pgp/server-6.0.asc | sudo apt-key add -

# Create list file
echo "deb [ arch=amd64,arm64 ] https://repo.mongodb.org/apt/ubuntu jammy/mongodb-org/6.0 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-6.0.list

# Update and install
sudo apt-get update
sudo apt-get install -y mongodb-org

# Start MongoDB
sudo systemctl start mongod
sudo systemctl enable mongod
```

#### On macOS:
```bash
# Using Homebrew
brew tap mongodb/brew
brew install mongodb-community
brew services start mongodb/brew/mongodb-community
```

#### On Windows:
1. Download MongoDB Community Server from https://www.mongodb.com/try/download/community
2. Run the installer and follow the setup wizard
3. Start MongoDB as a Windows service

### 2. Clone and Setup the Application

```bash
# Navigate to the project directory
cd siddesh

# Install Python dependencies
pip install -r requirements.txt

# Create environment file (optional)
cp .env.example .env  # Edit this file with your settings
```

### 3. Environment Configuration

Create a `.env` file or set environment variables:

```env
# Database Configuration
MONGODB_URL=mongodb://localhost:27017
DATABASE_NAME=aadhaar_masking_db
GRID_FS_BUCKET=encrypted_images

# Encryption Configuration (will be auto-generated in development)
ENCRYPTION_KEY=your_secret_encryption_key_here
SALT_KEY=your_salt_key_here

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
ENVIRONMENT=development

# Security Configuration
SESSION_SECRET=your_session_secret_here
```

**Note**: In development mode, encryption keys will be automatically generated if not provided.

### 4. Start the Application

```bash
# Method 1: Using the API directly
python api.py

# Method 2: Using uvicorn
uvicorn api:app --host 0.0.0.0 --port 8000 --reload

# Method 3: Using the run script
python run_api.py
```

### 5. Verify Installation

1. Open your browser and go to `http://localhost:8000`
2. Check the health endpoint: `http://localhost:8000/health`
3. Verify MongoDB connection in the health response

## 🔧 Configuration Options

### Database Configuration

```python
# In src/config.py
MONGODB_URL = "mongodb://localhost:27017"  # MongoDB connection string
DATABASE_NAME = "aadhaar_masking_db"       # Database name
GRID_FS_BUCKET = "encrypted_images"       # GridFS bucket for file storage
```

### Encryption Configuration

The system uses AES encryption with Fernet for secure data storage:

- **Automatic Key Generation**: In development mode, keys are auto-generated
- **Manual Key Setup**: For production, set `ENCRYPTION_KEY` and `SALT_KEY`
- **Key Derivation**: Uses PBKDF2-HMAC-SHA256 for key derivation

### API Configuration

```python
API_HOST = "0.0.0.0"          # Host to bind to
API_PORT = 8000               # Port to listen on
MAX_FILE_SIZE_MB = 10         # Maximum file size for uploads
MAX_BULK_FILES = 10           # Maximum files in bulk processing
```

## 🆕 New Features

### 1. Database Storage Endpoints

#### Process and Store Image
```bash
POST /process-and-store-image
# Automatically processes and stores image with encryption
```

#### Retrieve Stored Image
```bash
GET /retrieve-image/{record_id}/{image_type}
# image_type: 'original' or 'masked'
```

#### List Records with Pagination
```bash
GET /list-records?page=1&page_size=20&search=filename
```

#### Get Record Details
```bash
GET /get-record/{record_id}
```

#### Delete Record
```bash
DELETE /delete-record/{record_id}
```

#### System Statistics
```bash
GET /statistics
```

### 2. Enhanced Frontend Features

#### Storage Toggle
- Checkbox option to store processed images in database
- Real-time feedback on storage status

#### Records Management Tab
- **View Records**: Paginated table of all stored records
- **Search**: Search records by filename
- **Record Details**: Modal view with full record information
- **Download**: Download original or masked images
- **Delete**: Remove records and associated files

#### Statistics Dashboard
- Total records count
- Recent activity (24-hour)
- Database size information
- Encryption status

### 3. Security Features

#### Encryption
- **Images**: AES encryption before database storage
- **UIDs**: Encrypted Aadhaar numbers in database
- **Files**: Secure GridFS storage with encryption

#### Access Control
- Secure API endpoints
- Proper error handling without data exposure
- Secure key management

## 🔍 API Usage Examples

### Process Image with Storage
```javascript
const formData = new FormData();
formData.append('file', imageFile);

// Using the storage endpoint
const response = await fetch('/process-and-store-image', {
    method: 'POST',
    body: formData
});

// Using existing endpoint with storage flag
const response2 = await fetch('/process-image?store=true', {
    method: 'POST',
    body: formData
});
```

### Retrieve Stored Records
```javascript
// Get paginated records
const records = await fetch('/list-records?page=1&page_size=10');

// Search records
const searchResults = await fetch('/list-records?search=aadhaar');

// Get specific record
const record = await fetch('/get-record/60f7b3b3b3b3b3b3b3b3b3b3');
```

### Download Stored Images
```javascript
// Download masked image
const response = await fetch('/retrieve-image/60f7b3b3b3b3b3b3b3b3b3b3/masked');
const blob = await response.blob();
const url = URL.createObjectURL(blob);

// Trigger download
const a = document.createElement('a');
a.href = url;
a.download = 'masked_image.png';
a.click();
```

## 🧪 Testing the Enhanced System

### 1. Basic Functionality Test
1. Upload an Aadhaar card image
2. Check "Store in secure database" option
3. Process the image
4. Verify storage success message

### 2. Records Management Test
1. Go to "Records" tab
2. Verify stored records appear
3. Search for specific records
4. View record details
5. Download images
6. Delete a test record

### 3. API Health Check
```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
    "status": "healthy",
    "timestamp": "2024-01-01T12:00:00",
    "database_connected": true,
    "encryption_ready": true,
    "version": "2.0.0"
}
```

## 🛡️ Security Considerations

### Production Deployment

1. **Set Strong Encryption Keys**:
   ```env
   ENCRYPTION_KEY=your_very_secure_key_here
   SALT_KEY=your_unique_salt_here
   ```

2. **Secure MongoDB**:
   - Enable authentication
   - Use SSL/TLS connections
   - Configure proper access controls

3. **API Security**:
   - Use HTTPS in production
   - Implement rate limiting
   - Add authentication if needed

4. **Environment Variables**:
   - Never commit `.env` files
   - Use secure environment variable management
   - Rotate keys regularly

### Data Privacy

- **Encryption at Rest**: All images and UIDs encrypted before storage
- **Secure Transmission**: Use HTTPS for all API calls
- **Access Logging**: Monitor who accesses what data
- **Data Retention**: Implement cleanup policies for old records

## 🔧 Troubleshooting

### Common Issues

#### MongoDB Connection Failed
```bash
# Check MongoDB status
sudo systemctl status mongod

# Restart MongoDB
sudo systemctl restart mongod

# Check logs
sudo tail -f /var/log/mongodb/mongod.log
```

#### Encryption Key Issues
- Ensure encryption keys are properly set
- In development, let the system auto-generate keys
- Check console output for generated keys

#### Permission Errors
```bash
# Fix directory permissions
chmod 755 uploads output static
```

#### API Not Responding
- Check if port 8000 is already in use
- Verify all dependencies are installed
- Check console for error messages

### Performance Optimization

1. **MongoDB Indexing**: Indexes are automatically created for better performance
2. **File Size Limits**: Adjust `MAX_FILE_SIZE_MB` as needed
3. **Connection Pooling**: MongoDB connection pooling is configured
4. **Cleanup**: Use the cleanup endpoint to remove old records

## 📚 Additional Resources

### API Documentation
- Access interactive API docs at: `http://localhost:8000/docs`
- OpenAPI specification: `http://localhost:8000/openapi.json`

### Database Schema
```javascript
// processed_cards collection
{
    "_id": ObjectId,
    "encrypted_uid": Binary,           // Encrypted Aadhaar number
    "original_image_id": ObjectId,     // GridFS file ID
    "masked_image_id": ObjectId,       // GridFS file ID
    "filename": String,                // Original filename
    "processing_metadata": {
        "processing_time": Number,
        "locations_found": Number,
        "uid_numbers_count": Number,
        "file_size_original": Number,
        "file_size_masked": Number,
        "image_format": String
    },
    "created_at": Date,
    "updated_at": Date,
    "status": String                   // "processing", "completed", "failed"
}
```

### File Structure
```
siddesh/
├── api.py                 # Enhanced main API file
├── src/
│   ├── config.py         # Configuration management
│   ├── database.py       # MongoDB operations
│   ├── encryption.py     # Encryption utilities
│   ├── storage.py        # Secure storage manager
│   ├── models.py         # Data models
│   ├── ocr_detector.py   # OCR detection (existing)
│   └── image_masker.py   # Image masking (existing)
├── uploads/              # Temporary upload directory
├── output/               # Temporary output directory
├── static/               # Static files (temporary)
├── requirements.txt      # Python dependencies
└── ENHANCED_SETUP.md     # This setup guide
```

## 🎯 Next Steps

1. **Test the System**: Follow the testing procedures above
2. **Customize Configuration**: Adjust settings as needed
3. **Security Review**: Implement additional security measures for production
4. **Monitoring**: Set up logging and monitoring for production use
5. **Backup Strategy**: Implement regular database backups

For support or questions, refer to the original README.md or create an issue in the repository.

---

**Security Notice**: This system handles sensitive data. Always follow security best practices and comply with relevant data protection regulations. 