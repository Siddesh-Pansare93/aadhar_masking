# 🎨 Frontend Setup Guide

## Quick Start

### 1. Start the API Server
```bash
cd siddesh
python run_api.py
```

### 2. Open the Frontend
Simply open `index.html` in your web browser or use a local server:

**Option A: Direct File Opening**
- Open `siddesh/index.html` in any modern web browser

**Option B: Local HTTP Server (Recommended)**
```bash
# Using Python's built-in server
cd siddesh
python -m http.server 3000

# Then open: http://localhost:3000
```

**Option C: Using Node.js**
```bash
# Install a simple HTTP server
npm install -g http-server

# Run in the siddesh directory
cd siddesh
http-server -p 3000

# Then open: http://localhost:3000
```

## 🌟 Features

### Modern UI Design
- **Beautiful gradient design** with professional styling
- **Responsive layout** that works on desktop and mobile
- **Smooth animations** and hover effects
- **Clean typography** using modern system fonts

### Single Image Processing
- 📸 **Drag & drop** or click to upload
- ⚡ **Real-time progress** indicator with spinner
- 📊 **Detailed results** showing processing time and locations
- 🖼️ **Live image preview** of masked results
- 📥 **Download button** for masked images

### Bulk Image Processing
- 📚 **Multiple file selection** (up to 10 images)
- 📝 **File list management** with individual remove options
- 📈 **Summary statistics** dashboard
- 🔍 **Individual result cards** for each processed image
- ❌ **Error handling** with detailed error messages

### User Experience Features
- 🎛️ **Tab-based interface** for easy navigation
- 🎨 **Visual feedback** for all interactions
- 📱 **Mobile responsive** design
- 🔄 **Auto-clear results** when switching tabs
- 🎯 **Smart file validation** (images only)

## 📋 Usage Instructions

### For Single Images:
1. Click on the "📄 Single Image" tab
2. Drag & drop an image or click the upload area
3. Click "Process Image" button
4. View results and download the masked image

### For Bulk Processing:
1. Click on the "📚 Bulk Processing" tab
2. Select multiple images (up to 10)
3. Review the file list and remove unwanted files if needed
4. Click "Process All Images" button
5. View the summary and individual results
6. Download each masked image individually

## 🎨 Styling Features

### Color Scheme
- **Primary Gradient**: Purple to blue (`#667eea` to `#764ba2`)
- **Success**: Green tones for successful operations
- **Error**: Red tones for error states
- **Neutral**: Gray tones for secondary information

### Layout
- **Max-width**: 1200px for optimal readability
- **Card-based design** for organized content
- **Grid layouts** for responsive result displays
- **Smooth borders** and shadows for modern look

### Interactive Elements
- **Hover effects** on buttons and upload areas
- **Loading spinners** for processing feedback
- **File drag-and-drop** with visual feedback
- **Responsive tabs** that adapt to screen size

## 🖼️ Image Display Features

- **Automatic scaling** to fit container
- **Rounded corners** for modern appearance
- **Drop shadows** for depth effect
- **Download links** for easy file access
- **Responsive sizing** based on screen size

## 📱 Mobile Compatibility

The frontend is fully responsive and includes:
- **Stacked layouts** on small screens
- **Touch-friendly** button sizes
- **Optimized typography** for mobile reading
- **Simplified navigation** for mobile devices

## 🚀 Performance Features

- **Efficient file handling** with proper cleanup
- **Minimal JavaScript** for fast loading
- **CSS3 animations** for smooth interactions
- **Optimized images** and assets

## 🔧 Customization

You can easily customize the frontend by:
- **Modifying colors** in the CSS variables
- **Adjusting layouts** in the grid definitions
- **Changing API endpoint** in the JavaScript constants
- **Adding new features** to the existing structure

## 📚 Browser Support

Works with all modern browsers:
- ✅ Chrome 60+
- ✅ Firefox 55+
- ✅ Safari 11+
- ✅ Edge 16+

## 🐛 Troubleshooting

### Common Issues:

**1. Images not displaying:**
- Ensure the API server is running on `http://localhost:8000`
- Check browser console for CORS errors

**2. Upload not working:**
- Verify file types are images (JPG, PNG, etc.)
- Check file size limits

**3. API connection failed:**
- Confirm the API server is running
- Check the API_BASE_URL in the JavaScript code

**4. Mobile issues:**
- Use a local HTTP server instead of opening file directly
- Ensure touch events are working properly 