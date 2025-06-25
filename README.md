# Aadhaar Masking Project

A Python application that detects Aadhaar numbers from card images using OCR and masks the first 4 digits for privacy protection.

## 🎯 Project Overview

This project implements a two-step process:
1. **OCR Detection**: Extract Aadhaar numbers from card images using advanced OCR techniques
2. **Number Masking**: Replace the first 4 digits with 'X' characters (e.g., "1234 5678 9012" → "XXXX 5678 9012")

## 🛠️ Features

- **Multiple OCR Engines**: Support for both EasyOCR and Tesseract
- **Image Preprocessing**: Advanced image processing for better OCR accuracy
- **Robust Pattern Matching**: Multiple regex patterns to detect Aadhaar numbers
- **Error Handling**: Comprehensive error handling and logging
- **Command Line Interface**: Easy-to-use CLI for batch processing
- **Extensible Design**: Modular architecture for future enhancements

## 📁 Project Structure

```
aadhar_masking/
├── src/
│   ├── __init__.py
│   ├── ocr_detector.py      # OCR detection logic
│   └── image_masker.py      # Image masking functionality
├── sample_data/             # Directory for test images
├── main.py                  # Main application entry point
├── requirements.txt         # Python dependencies
└── README.md               # This file
```

## 🚀 Setup and Installation

### 1. Clone or Navigate to Project Directory

```bash
cd aadhar_masking
```

### 2. Create Virtual Environment (Recommended)

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Install Tesseract (Optional - for Tesseract OCR)

- **Windows**: Download from [UB Mannheim](https://github.com/UB-Mannheim/tesseract/wiki)
- **Linux**: `sudo apt-get install tesseract-ocr`
- **Mac**: `brew install tesseract`

## 💻 Usage

### Quick Demo

Run without arguments to see a demo:

```bash
python main.py
```

### Process Aadhaar Card Image

```bash
# Basic usage with EasyOCR and Tesseract
python main.py --image path/to/aadhaar_card.jpg

# Specify output file for masked image
python main.py --image sample_data/aadhaar.jpg --output output/masked_aadhaar.jpg

# Use specific OCR method
python main.py --image sample_data/aadhaar.jpg --ocr-method easyocr
```

### Command Line Options

- `--image`, `-i`: Path to the Aadhaar card image (required)
- `--output`, `-o`: Output path for masked image (optional)
- `--ocr-method`: Choose OCR method (`easyocr`, `tesseract`, `both`)

## 🔧 Configuration

### Environment Variables

Create a `.env` file for configuration:

```env
# OCR Configuration
DEFAULT_OCR_METHOD=easyocr
TESSERACT_PATH=C:\Program Files\Tesseract-OCR\tesseract.exe

# Logging
LOG_LEVEL=INFO
```

## 📊 OCR Detection Process

### 1. Image Preprocessing
- Convert to grayscale
- Apply Gaussian blur for noise reduction
- Adaptive thresholding
- Morphological operations

### 2. Text Extraction
- **EasyOCR**: Deep learning-based OCR with high accuracy
- **Tesseract**: Traditional OCR with custom configuration for digits

### 3. Aadhaar Number Pattern Matching
- Pattern 1: 12 continuous digits (`\b\d{12}\b`)
- Pattern 2: 4-4-4 format with spaces (`\b\d{4}\s+\d{4}\s+\d{4}\b`)
- Pattern 3: Flexible spacing (`\b(?:\d{4}[\s]*){3}\b`)

## 🎭 Masking Process

The masking process converts:
- **Input**: `1234 5678 9012`
- **Output**: `XXXX 5678 9012`

## 📝 Example Output

```
🔍 Aadhaar Card OCR Detection Started...
📸 Processing image: sample_data/aadhaar_card.jpg
✅ Aadhaar Number Detected: 1234 5678 9012
🎭 Masked Aadhaar Number: XXXX 5678 9012
💾 Masked image saved: output/masked_aadhaar.jpg
```

## 🧪 Testing

Place test Aadhaar card images in the `sample_data/` folder and run:

```bash
python main.py --image sample_data/test_aadhaar.jpg --output output/masked_test.jpg
```

## 🔍 Troubleshooting

### Common Issues

1. **No Aadhaar number detected**:
   - Ensure image is clear and well-lit
   - Check that Aadhaar number is fully visible
   - Try different OCR methods

2. **Import errors**:
   - Verify all dependencies are installed: `pip install -r requirements.txt`
   - Check Python version (3.7+ recommended)

3. **Tesseract errors**:
   - Install Tesseract OCR
   - Update Tesseract path in configuration

### Performance Tips

- Use high-resolution, clear images
- Ensure good lighting conditions
- Avoid blurry or rotated images
- EasyOCR generally performs better than Tesseract for Aadhaar cards

## 🚧 Current Limitations

1. **Image Masking**: Currently adds overlay text instead of replacing original text
2. **Text Location**: Text location detection needs enhancement for precise replacement
3. **Format Variations**: May need adjustment for different Aadhaar card layouts

## 🔮 Future Enhancements

1. **Roboflow Integration**: Custom trained models for better accuracy
2. **Advanced Image Masking**: Precise text location and replacement
3. **Batch Processing**: Process multiple images simultaneously
4. **Web Interface**: User-friendly web application
5. **Mobile App**: Mobile application for on-the-go masking

## 📜 License

This project is for educational and research purposes. Please ensure compliance with data privacy regulations when processing personal documents.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📞 Support

For issues and questions:
1. Check the troubleshooting section
2. Review error logs
3. Create an issue with detailed information 