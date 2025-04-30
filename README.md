<<<<<<< HEAD
# CCTV_FACE_RECOGNITION
=======
# Face Recognition System

A real-time face detection and recognition system using OpenCV and Flask that displays the webcam feed on a web page.

## Features

- Real-time face detection using OpenCV's Haar Cascade classifier
- Face recognition to identify known faces
- Ability to add new faces to the known faces database
- Web interface using Flask
- Live webcam feed displayed on the web page
- Responsive design

## Requirements

- Python 3.7+
- Webcam
- For Linux environments, you may need to install additional libraries:
  ```
  sudo apt-get install cmake
  sudo apt-get install libboost-all-dev
  sudo apt-get install build-essential
  ```

## Installation

1. Clone this repository:
```
git clone https://github.com/yourusername/face-recognition-system.git
cd face-recognition-system
```

2. Install the required packages:
```
pip install -r requirements.txt
```

## Usage

1. Run the Flask application:
```
python app.py
```

2. Open your web browser and navigate to:
```
http://127.0.0.1:5000/
```

3. Allow access to your webcam when prompted by the browser.

4. The system will automatically detect faces in the video feed:
   - Unknown faces will be labeled as "Unknown"
   - Known faces will be labeled with their name

5. To add a new face to the system:
   - Enter the person's name in the input field
   - Click "Capture Image" to take a snapshot
   - Review the captured image
   - Click "Add Face" to add the person to the known faces database

## How it Works

- The application captures video from your webcam using OpenCV
- Each frame is processed to detect faces using Haar Cascade classifier
- Detected faces are compared against known faces using the face_recognition library
- Recognized faces are labeled with their name, unknown faces are labeled as "Unknown"
- The processed video stream is sent to the web interface using Flask's Response class
- The web page displays the video feed in real-time
- Users can add new faces to the database through the web interface

## Face Recognition Algorithm

This system uses the face_recognition library which is built on dlib's state-of-the-art face recognition built with deep learning. The model has an accuracy of 99.38% on the Labeled Faces in the Wild benchmark.

## Troubleshooting

- If the webcam doesn't start, make sure no other application is using it
- Ensure you have the correct permissions for accessing the webcam
- Adjust the lighting in your environment for better face detection and recognition
- If faces are not being recognized correctly, try adding multiple images of the same person at different angles

## License

This project is licensed under the MIT License - see the LICENSE file for details. 
>>>>>>> master
