from flask import Flask, render_template, Response, jsonify, request
import cv2
import numpy as np
import time
import base64
import os
from datetime import datetime

app = Flask(__name__)

# Global variables
drowsiness_detected = False
alert_active = False
face_cascade = None
eye_cascade = None
EYE_AR_THRESH = 0.3  # Was 0.25, increased for better sensitivity
EYE_AR_CONSEC_FRAMES = 15  # Was 20, decreased to trigger alert faster
COUNTER = 0

def initialize_opencv():
    global face_cascade, eye_cascade
    try:
        # Load the pre-trained Haar cascade classifiers
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        eye_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_eye.xml')
        
        # Check if cascades were loaded correctly
        if face_cascade.empty():
            print("ERROR: Failed to load face cascade classifier!")
            raise Exception("Failed to load face cascade classifier")
        
        if eye_cascade.empty():
            print("ERROR: Failed to load eye cascade classifier!")
            raise Exception("Failed to load eye cascade classifier")
            
        print("OpenCV initialized successfully with face and eye detection models")
    except Exception as e:
        print(f"Error initializing OpenCV: {str(e)}")
        raise

def eye_aspect_ratio(eye):
    """
    Calculate the eye aspect ratio to determine if an eye is open or closed.
    A lower ratio typically indicates a closed eye.
    
    This is a simplified version that uses the height/width ratio, 
    but also incorporates brightness to better detect eye closure.
    """
    if eye.size == 0:
        return 0
    
    height, width = eye.shape[:2]
    
    # Basic geometric ratio
    geometric_ratio = height / width if width > 0 else 0
    
    # Calculate average brightness of the eye region
    avg_brightness = cv2.mean(eye)[0] / 255.0  # Normalize to 0-1
    
    # Combine geometric ratio with brightness
    # Closed eyes typically have less brightness variation
    brightness_factor = 0.7 + (0.3 * avg_brightness)  # Scale factor
    
    # Final EAR
    ear = geometric_ratio * brightness_factor
    
    return ear

def detect_drowsiness(frame):
    global COUNTER, drowsiness_detected, alert_active
    
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    
    # Apply histogram equalization to improve contrast
    gray = cv2.equalizeHist(gray)
    
    # Detect faces with more relaxed parameters
    faces = face_cascade.detectMultiScale(
        gray,
        scaleFactor=1.2,  # Was 1.1, increased for better detection
        minNeighbors=3,   # Was 5, decreased for more detections
        minSize=(30, 30)
    )
    
    # Reset drowsiness flag if no faces detected
    if len(faces) == 0:
        COUNTER = 0
        drowsiness_detected = False
        # Add text to frame for debugging
        cv2.putText(frame, "No faces detected", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        return frame
    
    # Process each face
    for (x, y, w, h) in faces:
        cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
        
        # Region of interest for the face
        roi_gray = gray[y:y+h, x:x+w]
        roi_color = frame[y:y+h, x:x+w]
        
        # Detect eyes with more relaxed parameters
        eyes = eye_cascade.detectMultiScale(
            roi_gray,
            scaleFactor=1.1,
            minNeighbors=2,  # Was implicitly 5, decreased for more detections
            minSize=(20, 20)  # Was implicitly default, decreased for smaller eyes
        )
        
        # Add text to show how many eyes were detected
        cv2.putText(frame, f"Eyes detected: {len(eyes)}", (10, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)
        
        if len(eyes) >= 2:  # At least two eyes detected
            # Reset counter if eyes are open
            COUNTER = 0
            drowsiness_detected = False
            
            # Draw rectangles around eyes
            for (ex, ey, ew, eh) in eyes:
                cv2.rectangle(roi_color, (ex, ey), (ex+ew, ey+eh), (255, 0, 0), 2)
                
                # Extract eye region
                eye_roi = roi_gray[ey:ey+eh, ex:ex+ew]
                
                # Calculate eye aspect ratio (simplified)
                ear = eye_aspect_ratio(eye_roi)
                
                # Add text to show EAR value
                cv2.putText(frame, f"EAR: {ear:.2f}", (10, 90),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)
                
                # Check if eye is closed based on aspect ratio
                if ear < EYE_AR_THRESH:
                    COUNTER += 1
                else:
                    COUNTER = 0
        else:
            # If eyes are not detected, increment counter
            COUNTER += 1
        
        # Add text to show counter value
        cv2.putText(frame, f"Counter: {COUNTER}/{EYE_AR_CONSEC_FRAMES}", (10, 120),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        # Check if drowsiness is detected
        if COUNTER >= EYE_AR_CONSEC_FRAMES:
            drowsiness_detected = True
            cv2.putText(frame, "DROWSINESS ALERT!", (10, 150),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        else:
            drowsiness_detected = False
    
    return frame

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/detect', methods=['POST'])
def detect():
    # Get the image data from the request
    image_data = request.json.get('image')
    
    if not image_data:
        return jsonify({'error': 'No image data provided'}), 400
    
    try:
        # Remove the data URL prefix (e.g., 'data:image/jpeg;base64,')
        if ',' in image_data:
            image_data = image_data.split(',')[1]
        
        # Decode the base64 image
        image_bytes = base64.b64decode(image_data)
        
        # Convert to numpy array
        nparr = np.frombuffer(image_bytes, np.uint8)
        
        # Decode image
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if frame is None:
            return jsonify({'error': 'Could not decode image'}), 400
            
        # Resize image to improve performance (smaller size)
        height, width = frame.shape[:2]
        if width > 640:
            scale_factor = 640 / width
            frame = cv2.resize(frame, (0, 0), fx=scale_factor, fy=scale_factor)
        
        # Process frame for drowsiness detection
        processed_frame = detect_drowsiness(frame)
        
        # Encode the processed frame as base64
        # Lower JPEG quality (70%) for faster transfer
        encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 70]
        _, buffer = cv2.imencode('.jpg', processed_frame, encode_param)
        processed_image = base64.b64encode(buffer).decode('utf-8')
        
        # Return the result
        return jsonify({
            'drowsiness_detected': drowsiness_detected,
            'processed_image': 'data:image/jpeg;base64,' + processed_image
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/check_drowsiness')
def check_drowsiness():
    return jsonify({'drowsiness_detected': drowsiness_detected})

# Initialize OpenCV on startup
initialize_opencv()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=False, threaded=True) 
