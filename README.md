# Driver Drowsiness Detection System

A web-based application that uses computer vision to detect driver drowsiness through the browser webcam.

## Features

- Real-time drowsiness detection using browser webcam
- Alert system for drowsiness detection
- Session tracking and statistics
- Customizable settings (sensitivity, alert volume, etc.)
- Multiple camera support
- Adjustable frame rate

## Deployment on Render

This application is designed to be deployed on Render. Follow these steps to deploy:

1. Create a new Web Service on Render
2. Connect your GitHub repository
3. Use the following settings:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn app:app`
   - **Runtime:** Python 3
   - **Instance Type:** Free or Starter (based on your needs)

## Local Development

To run the application locally:

1. Clone the repository
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Run the application:
   ```
   python app.py
   ```
4. Open your browser and navigate to `http://localhost:5000`

## How It Works

1. The browser captures webcam frames using the `getUserMedia` API
2. Frames are converted to base64 images
3. Images are sent to the Flask backend via AJAX
4. The Flask backend processes the images using OpenCV for drowsiness detection
5. Results are sent back to the browser for display

## Technical Stack

- Frontend: HTML, CSS, JavaScript
- Backend: Flask (Python)
- Computer Vision: OpenCV
- Deployment: Render

## Notes

- This application uses browser-based webcam capture, making it suitable for cloud deployment
- For optimal performance, use a modern browser with good webcam support
- Adjust the frame rate in settings based on your connection speed 