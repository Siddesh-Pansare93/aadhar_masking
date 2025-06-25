📸 HOW TO ADD AADHAAR IMAGES FOR TESTING
==========================================

1. PLACE YOUR IMAGES HERE:
   - Copy your Aadhaar card images to this folder
   - Supported formats: .jpg, .jpeg, .png, .bmp, .tiff

2. NAMING SUGGESTIONS:
   - aadhaar_front.jpg
   - aadhaar_back.jpg  
   - my_aadhaar.png
   - test_card.jpeg

3. IMAGE QUALITY TIPS:
   - Use high resolution images (at least 1000x600 pixels)
   - Ensure good lighting
   - Make sure Aadhaar number is clearly visible
   - Avoid blurry or rotated images

4. EXAMPLE COMMANDS TO TEST:
   python main.py --image sample_data/your_image_name.jpg
   python main.py --image sample_data/aadhaar_front.jpg --output output/masked_result.jpg

5. PRIVACY NOTE:
   - These are test images only
   - Never share real Aadhaar images publicly
   - Delete test images after testing if they contain real data 