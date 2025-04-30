from flask import Flask, render_template, Response, request, jsonify
import cv2
import os
import numpy as np
import base64
from datetime import datetime, time
import pickle
import threading
import time as time_module
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from twilio.rest import Client

app = Flask(__name__)

# Email configuration
SENDER_EMAIL = "agrawalsuryansh71@gmail.com"  # Replace with your Gmail account (or keep for testing)
SENDER_PASSWORD = "upnp fhhs vfqd zjgh"  # App password (16-character code)
RECIPIENT_EMAIL = "teamgarud123@gmail.com"  # Will be set by the user
MESSAGE_COOLDOWN = 90  # Minimum seconds between alerts (to prevent spam)
last_message_time = 0
email_alerts_enabled = False

# SMS configuration
RECIPIENT_PHONE = ""  # Recipient mobile number with country code
sms_alerts_enabled = False
last_sms_time = 0
SMS_COOLDOWN = 90  # Seconds between SMS alerts

# Load the OpenCV face detector
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

# Known faces directory
KNOWN_FACES_DIR = 'known_faces'
if not os.path.exists(KNOWN_FACES_DIR):
    os.makedirs(KNOWN_FACES_DIR)

# Model directory
MODEL_DIR = 'models'
if not os.path.exists(MODEL_DIR):
    os.makedirs(MODEL_DIR)

# Face recognizer model path
RECOGNIZER_PATH = os.path.join(MODEL_DIR, 'face_recognizer.yml')
LABELS_PATH = os.path.join(MODEL_DIR, 'face_labels.pkl')

# Initialize face recognizer
recognizer = cv2.face.LBPHFaceRecognizer_create()

# Store labels and their corresponding names
label_ids = {}
current_id = 0
label_names = {}  # Reverse mapping: id -> name

# Flag to enable/disable face recognition
face_recognition_enabled = True

# Scheduling variables
schedule_active = False
start_time = None
end_time = None
scheduler_thread = None
scheduler_running = False

# Global variables
face_recognition_enabled = True
recognizer = None
label_ids = {}
label_names = {}
known_faces = []

# Load recognizer if it exists
try:
    recognizer = cv2.face.LBPHFaceRecognizer_create()
    recognizer.read(RECOGNIZER_PATH)
    with open(LABELS_PATH, 'rb') as f:
        label_ids = pickle.load(f)
        # Invert the dictionary to get name->id mapping
        label_names = {v: k for k, v in label_ids.items()}
    print(f"Loaded recognizer with {len(label_ids)} known people")
except Exception as e:
    print(f"Could not load recognizer: {e}")
    recognizer = cv2.face.LBPHFaceRecognizer_create()
    label_ids = {}
    label_names = {}

def send_email_alert(subject, message):
    """Send email alert using SMTP."""
    global last_message_time, SENDER_EMAIL, SENDER_PASSWORD, RECIPIENT_EMAIL
    
    # Debug logs
    print(f"Email Alert Function Called with subject: {subject}")
    print(f"Email settings: Enabled={email_alerts_enabled}, Recipient={RECIPIENT_EMAIL}")
    
    # Check if email alerts are enabled
    if not email_alerts_enabled:
        print("Email alerts are disabled")
        return False
    
    # Check if the recipient email is set
    if not RECIPIENT_EMAIL:
        print("Recipient email not configured")
        return False
    
    # Check cooldown period
    current_time = time_module.time()
    if current_time - last_message_time < MESSAGE_COOLDOWN:
        print(f"Message cooldown period active. Waiting {MESSAGE_COOLDOWN} seconds between alerts.")
        return False
    
    # Send the email
    try:
        print(f"Attempting to send email to {RECIPIENT_EMAIL} from {SENDER_EMAIL}")
        
        # Create message container
        msg = MIMEMultipart()
        msg['From'] = SENDER_EMAIL
        msg['To'] = RECIPIENT_EMAIL
        msg['Subject'] = subject
        
        # Add body to email
        msg.attach(MIMEText(message, 'plain'))
        
        try:
            # Create SMTP session
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()  # Enable security
            
            # Login to sender email
            print(f"Attempting to login with {SENDER_EMAIL}")
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            
            # Send email
            text = msg.as_string()
            server.sendmail(SENDER_EMAIL, RECIPIENT_EMAIL, text)
            
            # Close connection
            server.quit()
            
            print(f"Email sent successfully to {RECIPIENT_EMAIL}")
            last_message_time = current_time
            return True
        except smtplib.SMTPAuthenticationError as auth_error:
            print(f"Gmail authentication error: {auth_error}")
            print("Please use an App Password instead of your regular password.")
            print("Generate an App Password at: https://myaccount.google.com/apppasswords")
            return False
        except smtplib.SMTPSenderRefused as sender_error:
            print(f"Sender refused error: {sender_error}")
            print("Make sure your Gmail account has less secure app access enabled or use an App Password.")
            return False
        except smtplib.SMTPRecipientsRefused as recipient_error:
            print(f"Recipient refused error: {recipient_error}")
            print("Check that the recipient email address is valid.")
            return False
        except smtplib.SMTPDataError as data_error:
            print(f"SMTP data error: {data_error}")
            return False
        except smtplib.SMTPException as smtp_error:
            print(f"General SMTP error: {smtp_error}")
            return False
    except Exception as e:
        print(f"Error sending email: {e}")
        return False

def send_sms_alert(message):
    """Send SMS alert using Twilio."""
    global last_sms_time, RECIPIENT_PHONE, sms_alerts_enabled
    
    # Debug logs
    print(f"SMS Alert Function Called with message: {message}")
    print(f"SMS settings: Enabled={sms_alerts_enabled}, Recipient={RECIPIENT_PHONE}")
    
    # Check if SMS alerts are enabled
    if not sms_alerts_enabled:
        print("SMS alerts are disabled")
        return False
    
    # Check if the recipient phone number is set
    if not RECIPIENT_PHONE:
        print("Recipient phone number not configured")
        return False
    
    # Check cooldown period
    current_time = time_module.time()
    if current_time - last_sms_time < SMS_COOLDOWN:
        print(f"SMS cooldown period active. Waiting {SMS_COOLDOWN} seconds between alerts.")
        return False
    
    try:
        # Format phone number (add +91 if not present)
        phone = RECIPIENT_PHONE
        if not phone.startswith('+'):
            phone = '+91' + phone
        
        # Send test message using dummy function instead of actual Twilio
        # In a real implementation, you would use Twilio API here
        print(f"[SMS ALERT] To: {phone}, Message: {message}")
        
        # Record the last SMS time
        last_sms_time = current_time
        return True
    except Exception as e:
        print(f"Error sending SMS: {e}")
        return False

def train_recognizer():
    """Train the face recognizer with the known faces."""
    global label_ids, current_id, label_names, recognizer
    
    # Reset for retraining
    label_ids = {}
    current_id = 0
    label_names = {}
    
    training_data = []
    labels = []
    
    # Iterate through known faces directory
    for filename in os.listdir(KNOWN_FACES_DIR):
        if filename.endswith('.jpg') or filename.endswith('.png'):
            # Get the name from the filename (without extension)
            name = os.path.splitext(filename)[0]
            if '_' in name:  # Extract name from "name_timestamp.jpg" format
                name = name.split('_')[0]
            
            # Load the image
            image_path = os.path.join(KNOWN_FACES_DIR, filename)
            image = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
            
            if image is None:
                print(f"Could not read {image_path}")
                continue
            
            # Detect faces in the image
            try:
                faces = face_cascade.detectMultiScale(image, 1.3, 5)
                
                # Process each face in the image
                for (x, y, w, h) in faces:
                    roi = image[y:y+h, x:x+w]
                    
                    # Resize to a consistent size for training
                    roi = cv2.resize(roi, (100, 100))
                    
                    # Assign a label ID to the name if not already assigned
                    if name not in label_ids:
                        label_ids[name] = current_id
                        label_names[current_id] = name
                        current_id += 1
                    
                    # Add the face image and its label to the training data
                    training_data.append(roi)
                    labels.append(label_ids[name])
            except Exception as e:
                print(f"Error processing image {image_path}: {e}")
                continue
    
    # Train the recognizer if we have face data
    if training_data and len(training_data) > 0:
        try:
            # Convert training data to numpy array
            np_training_data = [np.array(img, dtype=np.uint8) for img in training_data]
            np_labels = np.array(labels, dtype=np.int32)
            
            # Create a new recognizer instance for training
            recognizer = cv2.face.LBPHFaceRecognizer_create()
            recognizer.train(np_training_data, np_labels)
            
            # Save the trained model and labels
            recognizer.write(RECOGNIZER_PATH)
            
            with open(LABELS_PATH, 'wb') as f:
                pickle.dump({"label_ids": label_ids, "label_names": label_names, "current_id": current_id}, f)
                
            print(f"Trained recognizer with {len(training_data)} images of {len(label_ids)} people")
            return True
        except Exception as e:
            print(f"Error training recognizer: {e}")
            return False
    else:
        print("No faces found for training")
        return False

def load_recognizer():
    """Load the pre-trained face recognizer if it exists."""
    global label_ids, current_id, label_names, recognizer
    
    if os.path.exists(RECOGNIZER_PATH) and os.path.exists(LABELS_PATH):
        try:
            # Load the recognizer
            recognizer = cv2.face.LBPHFaceRecognizer_create()
            recognizer.read(RECOGNIZER_PATH)
                
            # Load the label mappings
            with open(LABELS_PATH, 'rb') as f:
                data = pickle.load(f)
                label_ids = data["label_ids"]
                label_names = data["label_names"]
                current_id = data["current_id"]
                
            print(f"Loaded recognizer with {len(label_ids)} known people")
            return True
        except Exception as e:
            print(f"Error loading recognizer: {e}")
            return False
    else:
        return train_recognizer()

# Try to load the recognizer, or train if not available
try:
    if not load_recognizer():
        print("Initializing new face recognizer")
except Exception as e:
    print(f"Error initializing face recognizer: {e}")

def scheduler_loop():
    """Background thread to check and update recognition status based on schedule."""
    global face_recognition_enabled, scheduler_running
    
    scheduler_running = True
    
    while scheduler_running and schedule_active:
        current_time = datetime.now().time()
        
        # Check if current time is within scheduled time range
        if start_time and end_time:
            # Handle case where end time is on the next day
            if start_time > end_time:
                should_be_enabled = current_time >= start_time or current_time <= end_time
            else:
                should_be_enabled = start_time <= current_time <= end_time
                
            # Only update if the status needs to change
            if face_recognition_enabled != should_be_enabled:
                face_recognition_enabled = should_be_enabled
                print(f"Scheduler: Face recognition turned {'ON' if should_be_enabled else 'OFF'}")
        
        # Sleep for 30 seconds before checking again
        time_module.sleep(30)
    
    scheduler_running = False
    print("Scheduler stopped")

def start_scheduler():
    """Start the scheduler thread."""
    global scheduler_thread, scheduler_running
    
    if not scheduler_running:
        scheduler_thread = threading.Thread(target=scheduler_loop)
        scheduler_thread.daemon = True
        scheduler_thread.start()
        print("Scheduler started")

def stop_scheduler():
    """Stop the scheduler thread."""
    global scheduler_running
    scheduler_running = False
    print("Stopping scheduler...")

def generate_frames():
    """Generate frames from camera with face recognition."""
    global face_recognition_enabled, recognizer, label_names
    
    # Initialize the camera
    camera = cv2.VideoCapture(0)
    
    if not camera.isOpened():
        print("Error: Could not open camera.")
        return
    
    while True:
        # Capture frame-by-frame
        success, frame = camera.read()
        if not success:
            break
        
        # Get the current time to display on the frame
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Convert to grayscale for face detection
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Detect faces
        faces = face_cascade.detectMultiScale(gray, 1.3, 5)
        
        # Flag to track if any unknown faces are detected
        unknown_face_detected = False
        
        # Process each face if face recognition is enabled
        if face_recognition_enabled and len(faces) > 0:
            for (x, y, w, h) in faces:
                # Draw rectangle around the face
                cv2.rectangle(frame, (x, y), (x+w, y+h), (255, 0, 0), 2)
                
                # Get region of interest for recognition
                roi_gray = gray[y:y+h, x:x+w]
                
                # Check if recognizer is loaded and has training data
                if recognizer is not None:
                    try:
                        # Resize ROI for recognition
                        roi_resized = cv2.resize(roi_gray, (100, 100))
                        
                        # Predict the face
                        id_, confidence = recognizer.predict(roi_resized)
                        
                        # Lower confidence means better match (0 is perfect match)
                        if confidence < 70:  # Confidence threshold
                            # Get the name if it exists in our label_names
                            if id_ in label_names:
                                name = label_names[id_]
                                confidence_text = f"{int(100 - confidence)}%"
                                
                                # Display name and confidence
                                cv2.putText(frame, f"{name} ({confidence_text})", 
                                            (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 
                                            0.8, (0, 255, 0), 2)
                            else:
                                # If ID not in label_names, mark as Unknown
                                cv2.putText(frame, "Unknown", (x, y-10), 
                                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
                                unknown_face_detected = True
                        else:
                            # If confidence too low, mark as Unknown
                            cv2.putText(frame, "Unknown", (x, y-10), 
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
                            unknown_face_detected = True
                    except Exception as e:
                        print(f"Error in face recognition: {e}")
                        cv2.putText(frame, "Error", (x, y-10), 
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
                else:
                    # If recognizer not loaded, mark as Unrecognized
                    cv2.putText(frame, "Unrecognized", (x, y-10), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
                    unknown_face_detected = True
        elif len(faces) > 0:
            # If face recognition is disabled but faces detected
            for (x, y, w, h) in faces:
                # Draw rectangle around the face
                cv2.rectangle(frame, (x, y), (x+w, y+h), (255, 0, 0), 2)
                cv2.putText(frame, "Face Detected", (x, y-10), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 0, 0), 2)
        
        # Send email alert if unknown face detected
        if unknown_face_detected:
            # Send email alert
            send_email_alert(
                "Unknown Face Detected", 
                f"An unknown face was detected at {current_time}. Please check your security system."
            )
            
            # Send SMS alert for unknown face
            send_sms_alert(
                f"ALERT: Unknown face detected at {current_time}. Please check your security system."
            )
        
        # Display the time on the frame
        cv2.putText(frame, current_time, (10, 30), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        
        # Display face recognition status
        status_text = "Face Recognition: ON" if face_recognition_enabled else "Face Recognition: OFF"
        cv2.putText(frame, status_text, (10, 60), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        
        # Convert to jpeg for streaming
        ret, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()
        
        # Yield the frame for streaming
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
    
    # Release the camera when done
from flask import Flask, render_template, Response, request, jsonify
import cv2
import os
import numpy as np
import base64
from datetime import datetime, time
import pickle
import threading
import time as time_module
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = Flask(__name__)

# Email configuration
SENDER_EMAIL = "agrawalsuryansh71@gmail.com"  # Replace with your Gmail account (or keep for testing)
SENDER_PASSWORD = "upnp fhhs vfqd zjgh"  # App password (16-character code)
RECIPIENT_EMAIL = "teamgarud123@gmail.com"  # Will be set by the user
MESSAGE_COOLDOWN = 90  # Minimum seconds between alerts (to prevent spam)
last_message_time = 0
email_alerts_enabled = False

# Load the OpenCV face detector
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

# Known faces directory
KNOWN_FACES_DIR = 'known_faces'
if not os.path.exists(KNOWN_FACES_DIR):
    os.makedirs(KNOWN_FACES_DIR)

# Model directory
MODEL_DIR = 'models'
if not os.path.exists(MODEL_DIR):
    os.makedirs(MODEL_DIR)

# Face recognizer model path
RECOGNIZER_PATH = os.path.join(MODEL_DIR, 'face_recognizer.yml')
LABELS_PATH = os.path.join(MODEL_DIR, 'face_labels.pkl')

# Initialize face recognizer
recognizer = cv2.face.LBPHFaceRecognizer_create()

# Store labels and their corresponding names
label_ids = {}
current_id = 0
label_names = {}  # Reverse mapping: id -> name

# Flag to enable/disable face recognition
face_recognition_enabled = True

# Scheduling variables
schedule_active = False
start_time = None
end_time = None
scheduler_thread = None
scheduler_running = False

# Global variables
face_recognition_enabled = True
recognizer = None
label_ids = {}
label_names = {}
known_faces = []

# Load recognizer if it exists
try:
    recognizer = cv2.face.LBPHFaceRecognizer_create()
    recognizer.read(RECOGNIZER_PATH)
    with open(LABELS_PATH, 'rb') as f:
        label_ids = pickle.load(f)
        # Invert the dictionary to get name->id mapping
        label_names = {v: k for k, v in label_ids.items()}
    print(f"Loaded recognizer with {len(label_ids)} known people")
except Exception as e:
    print(f"Could not load recognizer: {e}")
    recognizer = cv2.face.LBPHFaceRecognizer_create()
    label_ids = {}
    label_names = {}

def send_email_alert(subject, message):
    """Send email alert using SMTP."""
    global last_message_time, SENDER_EMAIL, SENDER_PASSWORD, RECIPIENT_EMAIL
    
    # Debug logs
    print(f"Email Alert Function Called with subject: {subject}")
    print(f"Email settings: Enabled={email_alerts_enabled}, Recipient={RECIPIENT_EMAIL}")
    
    # Check if email alerts are enabled
    if not email_alerts_enabled:
        print("Email alerts are disabled")
        return False
    
    # Check if the recipient email is set
    if not RECIPIENT_EMAIL:
        print("Recipient email not configured")
        return False
    
    # Check cooldown period
    current_time = time_module.time()
    if current_time - last_message_time < MESSAGE_COOLDOWN:
        print(f"Message cooldown period active. Waiting {MESSAGE_COOLDOWN} seconds between alerts.")
        return False
    
    # Send the email
    try:
        print(f"Attempting to send email to {RECIPIENT_EMAIL} from {SENDER_EMAIL}")
        
        # Create message container
        msg = MIMEMultipart()
        msg['From'] = SENDER_EMAIL
        msg['To'] = RECIPIENT_EMAIL
        msg['Subject'] = subject
        
        # Add body to email
        msg.attach(MIMEText(message, 'plain'))
        
        try:
            # Create SMTP session
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()  # Enable security
            
            # Login to sender email
            print(f"Attempting to login with {SENDER_EMAIL}")
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            
            # Send email
            text = msg.as_string()
            server.sendmail(SENDER_EMAIL, RECIPIENT_EMAIL, text)
            
            # Close connection
            server.quit()
            
            print(f"Email sent successfully to {RECIPIENT_EMAIL}")
            last_message_time = current_time
            return True
        except smtplib.SMTPAuthenticationError as auth_error:
            print(f"Gmail authentication error: {auth_error}")
            print("Please use an App Password instead of your regular password.")
            print("Generate an App Password at: https://myaccount.google.com/apppasswords")
            return False
        except smtplib.SMTPSenderRefused as sender_error:
            print(f"Sender refused error: {sender_error}")
            print("Make sure your Gmail account has less secure app access enabled or use an App Password.")
            return False
        except smtplib.SMTPRecipientsRefused as recipient_error:
            print(f"Recipient refused error: {recipient_error}")
            print("Check that the recipient email address is valid.")
            return False
        except smtplib.SMTPDataError as data_error:
            print(f"SMTP data error: {data_error}")
            return False
        except smtplib.SMTPException as smtp_error:
            print(f"General SMTP error: {smtp_error}")
            return False
    except Exception as e:
        print(f"Error sending email: {e}")
        return False

def train_recognizer():
    """Train the face recognizer with the known faces."""
    global label_ids, current_id, label_names, recognizer
    
    # Reset for retraining
    label_ids = {}
    current_id = 0
    label_names = {}
    
    training_data = []
    labels = []
    
    # Iterate through known faces directory
    for filename in os.listdir(KNOWN_FACES_DIR):
        if filename.endswith('.jpg') or filename.endswith('.png'):
            # Get the name from the filename (without extension)
            name = os.path.splitext(filename)[0]
            if '_' in name:  # Extract name from "name_timestamp.jpg" format
                name = name.split('_')[0]
            
            # Load the image
            image_path = os.path.join(KNOWN_FACES_DIR, filename)
            image = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
            
            if image is None:
                print(f"Could not read {image_path}")
                continue
            
            # Detect faces in the image
            try:
                faces = face_cascade.detectMultiScale(image, 1.3, 5)
                
                # Process each face in the image
                for (x, y, w, h) in faces:
                    roi = image[y:y+h, x:x+w]
                    
                    # Resize to a consistent size for training
                    roi = cv2.resize(roi, (100, 100))
                    
                    # Assign a label ID to the name if not already assigned
                    if name not in label_ids:
                        label_ids[name] = current_id
                        label_names[current_id] = name
                        current_id += 1
                    
                    # Add the face image and its label to the training data
                    training_data.append(roi)
                    labels.append(label_ids[name])
            except Exception as e:
                print(f"Error processing image {image_path}: {e}")
                continue
    
    # Train the recognizer if we have face data
    if training_data and len(training_data) > 0:
        try:
            # Convert training data to numpy array
            np_training_data = [np.array(img, dtype=np.uint8) for img in training_data]
            np_labels = np.array(labels, dtype=np.int32)
            
            # Create a new recognizer instance for training
            recognizer = cv2.face.LBPHFaceRecognizer_create()
            recognizer.train(np_training_data, np_labels)
            
            # Save the trained model and labels
            recognizer.write(RECOGNIZER_PATH)
            
            with open(LABELS_PATH, 'wb') as f:
                pickle.dump({"label_ids": label_ids, "label_names": label_names, "current_id": current_id}, f)
                
            print(f"Trained recognizer with {len(training_data)} images of {len(label_ids)} people")
            return True
        except Exception as e:
            print(f"Error training recognizer: {e}")
            return False
    else:
        print("No faces found for training")
        return False

def load_recognizer():
    """Load the pre-trained face recognizer if it exists."""
    global label_ids, current_id, label_names, recognizer
    
    if os.path.exists(RECOGNIZER_PATH) and os.path.exists(LABELS_PATH):
        try:
            # Load the recognizer
            recognizer = cv2.face.LBPHFaceRecognizer_create()
            recognizer.read(RECOGNIZER_PATH)
                
            # Load the label mappings
            with open(LABELS_PATH, 'rb') as f:
                data = pickle.load(f)
                label_ids = data["label_ids"]
                label_names = data["label_names"]
                current_id = data["current_id"]
                
            print(f"Loaded recognizer with {len(label_ids)} known people")
            return True
        except Exception as e:
            print(f"Error loading recognizer: {e}")
            return False
    else:
        return train_recognizer()

# Try to load the recognizer, or train if not available
try:
    if not load_recognizer():
        print("Initializing new face recognizer")
except Exception as e:
    print(f"Error initializing face recognizer: {e}")

def scheduler_loop():
    """Background thread to check and update recognition status based on schedule."""
    global face_recognition_enabled, scheduler_running
    
    scheduler_running = True
    
    while scheduler_running and schedule_active:
        current_time = datetime.now().time()
        
        # Check if current time is within scheduled time range
        if start_time and end_time:
            # Handle case where end time is on the next day
            if start_time > end_time:
                should_be_enabled = current_time >= start_time or current_time <= end_time
            else:
                should_be_enabled = start_time <= current_time <= end_time
                
            # Only update if the status needs to change
            if face_recognition_enabled != should_be_enabled:
                face_recognition_enabled = should_be_enabled
                print(f"Scheduler: Face recognition turned {'ON' if should_be_enabled else 'OFF'}")
        
        # Sleep for 30 seconds before checking again
        time_module.sleep(30)
    
    scheduler_running = False
    print("Scheduler stopped")

def start_scheduler():
    """Start the scheduler thread."""
    global scheduler_thread, scheduler_running
    
    if not scheduler_running:
        scheduler_thread = threading.Thread(target=scheduler_loop)
        scheduler_thread.daemon = True
        scheduler_thread.start()
        print("Scheduler started")

def stop_scheduler():
    """Stop the scheduler thread."""
    global scheduler_running
    scheduler_running = False
    print("Stopping scheduler...")

def generate_frames():
    """Function to capture video frames from webcam and perform face detection/recognition."""
    # Initialize webcam
    camera = cv2.VideoCapture(0)
    unknown_face_detected = False
    
    while True:
        # Read a frame from the camera
        success, frame = camera.read()
        if not success:
            break
        
        try:
            # Convert to grayscale for face detection
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            # Detect faces using OpenCV
            faces = face_cascade.detectMultiScale(gray, 1.3, 5)
            
            # Track if all faces in this frame are unknown
            current_frame_has_unknown = False
            
            # Process each detected face
            for (x, y, w, h) in faces:
                # Extract face region
                roi_gray = gray[y:y+h, x:x+w]
                
                # Draw a rectangle around the face (always show face detection)
                cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
                
                # Only perform face recognition if enabled
                if face_recognition_enabled:
                    # Only predict if we have trained data
                    name = "Unknown"
                    if len(label_ids) > 0:
                        try:
                            # Resize to match training size
                            resized_roi = cv2.resize(roi_gray, (100, 100))
                            
                            # Predict the face
                            id_, confidence = recognizer.predict(resized_roi)
                            
                            # Lower confidence means better match (LBPH returns distance, not probability)
                            if confidence < 80:  # Confidence threshold
                                name = label_names.get(id_, "Unknown")
                        except Exception as e:
                            print(f"Error in recognition: {e}")
                    
                    # Check if an unknown face was detected
                    if name == "Unknown":
                        current_frame_has_unknown = True
                        
                        # If this is the first detection of an unknown face, send an email alert
                        if not unknown_face_detected and email_alerts_enabled:
                            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            subject = f"ALERT: Unknown Face Detected"
                            alert_message = f"⚠️ ALERT: Unknown face detected on {timestamp} by your Face Recognition System."
                            send_email_alert(subject, alert_message)
                            unknown_face_detected = True
                    
                    # Draw a label with the name below the face
                    cv2.rectangle(frame, (x, y+h), (x+w, y+h+35), (0, 255, 0), cv2.FILLED)
                    cv2.putText(frame, name, (x+6, y+h+25), cv2.FONT_HERSHEY_DUPLEX, 0.8, (255, 255, 255), 1)
            
            # Reset the unknown face detected flag if no unknown faces in this frame
            if not current_frame_has_unknown:
                unknown_face_detected = False
            
            # Add status text showing if recognition is enabled
            status_text = "Recognition: ON" if face_recognition_enabled else "Recognition: OFF"
            cv2.putText(frame, status_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            
            # Add email alert status text
            email_status = "Email Alerts: ON" if email_alerts_enabled else "Email Alerts: OFF"
            cv2.putText(frame, email_status, (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            
            # Add schedule status if active
            if schedule_active:
                schedule_text = f"Scheduled: {start_time.strftime('%H:%M')} - {end_time.strftime('%H:%M')}"
                cv2.putText(frame, schedule_text, (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            
            # Encode the frame as JPEG
            ret, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()
            
            # Yield the frame in the byte format
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        except Exception as e:
            print(f"Error processing frame: {e}")
            # Provide a blank frame if there's an error
            blank_frame = np.zeros((480, 640, 3), np.uint8)
            ret, buffer = cv2.imencode('.jpg', blank_frame)
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

@app.route('/')
def home():
    """Home page with welcome message and navigation options."""
    # Count the number of known faces
    faces_count = len(label_ids)
    
    # Get email alert status
    alert_status = "Active" if email_alerts_enabled else "Disabled"
    
    # Get system status
    system_status = "Running" if face_recognition_enabled else "Paused"
    
    return render_template('home.html', 
                          known_faces_count=faces_count,
                          alert_status=alert_status,
                          system_status=system_status)

@app.route('/dashboard')
def index():
    """Dashboard page with live feed and controls."""
    return render_template('index.html')

@app.route('/profile')
def profile():
    """User profile and settings page."""
    return render_template('profile.html')

@app.route('/add_face_page')
def add_face_page():
    """Dedicated page for adding known faces."""
    return render_template('add_face.html')

@app.route('/video_feed')
def video_feed():
    """Route for the video feed."""
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/add_face', methods=['POST'])
def add_face():
    """Add a new known face from image data and name."""
    if 'image' not in request.json or 'name' not in request.json:
        return jsonify({'success': False, 'error': 'Missing image or name'}), 400
    
    image_data = request.json['image']
    name = request.json['name']
    
    # Validate name (alphanumeric only)
    if not name.replace(" ", "").isalnum():
        return jsonify({'success': False, 'error': 'Name should be alphanumeric'}), 400
    
    # Remove data URL prefix if present (e.g., "data:image/jpeg;base64,")
    if ',' in image_data:
        image_data = image_data.split(',')[1]
    
    try:
        # Decode base64 image
        image_bytes = base64.b64decode(image_data)
        
        # Create a temp file
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        file_path = os.path.join(KNOWN_FACES_DIR, f"{name}_{timestamp}.jpg")
        
        with open(file_path, 'wb') as f:
            f.write(image_bytes)
        
        # Verify the image contains a face
        image = cv2.imread(file_path, cv2.IMREAD_GRAYSCALE)
        if image is None:
            return jsonify({'success': False, 'error': 'Could not read image file'}), 400
        
        # Add error handling for face detection
        try:
            faces = face_cascade.detectMultiScale(image, 1.3, 5)
            
            if len(faces) == 0:
                # Remove the file if no face is detected
                os.remove(file_path)
                return jsonify({'success': False, 'error': 'No face detected in the image'}), 400
            
            # Retrain the recognizer with the new face
            if train_recognizer():
                return jsonify({'success': True, 'message': f'Face for {name} added successfully'})
            else:
                return jsonify({'success': False, 'error': 'Failed to train recognizer'}), 500
                
        except Exception as e:
            # Remove the file if there's an error
            os.remove(file_path)
            return jsonify({'success': False, 'error': f'Error detecting face: {str(e)}'}), 500
            
    except Exception as e:
        return jsonify({'success': False, 'error': f'Error processing image: {str(e)}'}), 500

@app.route('/known_faces')
def get_known_faces():
    """Get list of known faces."""
    faces = []
    for name in label_ids.keys():
        faces.append({'name': name})
    
    return jsonify({'faces': faces})

@app.route('/toggle_recognition', methods=['POST'])
def toggle_recognition():
    """Toggle face recognition on/off."""
    global face_recognition_enabled, schedule_active
    
    # If scheduled recognition is active, disable it
    if schedule_active:
        schedule_active = False
        stop_scheduler()
    
    # Toggle face recognition
    face_recognition_enabled = not face_recognition_enabled
    
    return jsonify({
        'success': True, 
        'enabled': face_recognition_enabled,
        'scheduled': False,
        'message': f'Face recognition turned {"ON" if face_recognition_enabled else "OFF"}'
    })

@app.route('/schedule_recognition', methods=['POST'])
def schedule_recognition():
    """Schedule face recognition for a specific time range."""
    global start_time, end_time, schedule_active
    
    if not request.json or 'start_time' not in request.json or 'end_time' not in request.json:
        return jsonify({'success': False, 'error': 'Missing start_time or end_time'}), 400
    
    try:
        # Parse time strings
        start_time_str = request.json['start_time']
        end_time_str = request.json['end_time']
        
        start_time = datetime.strptime(start_time_str, '%H:%M').time()
        end_time = datetime.strptime(end_time_str, '%H:%M').time()
        
        # Set the schedule active flag
        schedule_active = True
        
        # Start the scheduler
        start_scheduler()
        
        return jsonify({
            'success': True,
            'start_time': start_time_str,
            'end_time': end_time_str,
            'message': f'Face recognition scheduled from {start_time_str} to {end_time_str}'
        })
    except ValueError as e:
        return jsonify({'success': False, 'error': f'Invalid time format. Use HH:MM format. Error: {str(e)}'}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': f'Error setting schedule: {str(e)}'}), 500

@app.route('/cancel_schedule', methods=['POST'])
def cancel_schedule():
    """Cancel scheduled face recognition."""
    global schedule_active
    
    if schedule_active:
        schedule_active = False
        stop_scheduler()
        
        return jsonify({
            'success': True,
            'message': 'Scheduled face recognition canceled'
        })
    else:
        return jsonify({
            'success': False, 
            'error': 'No active schedule to cancel'
        }), 400

@app.route('/get_schedule', methods=['GET'])
def get_schedule():
    """Get current schedule status."""
    global schedule_active, start_time, end_time
    
    if schedule_active and start_time and end_time:
        return jsonify({
            'scheduled': True,
            'start_time': start_time.strftime('%H:%M'),
            'end_time': end_time.strftime('%H:%M')
        })
    else:
        return jsonify({
            'scheduled': False
        })

@app.route('/set_email', methods=['POST'])
def set_email():
    """Set the recipient email for alerts."""
    global RECIPIENT_EMAIL, email_alerts_enabled
    
    if not request.json or 'email' not in request.json:
        return jsonify({'success': False, 'error': 'Missing email address'}), 400
    
    email = request.json['email'].strip()
    
    # Basic email validation
    if not email or '@' not in email or '.' not in email:
        return jsonify({'success': False, 'error': 'Invalid email format'}), 400
    
    print(f"Setting recipient email: {email}")
    
    try:
        # Update the recipient email
        RECIPIENT_EMAIL = email
        
        # Enable email alerts automatically
        email_alerts_enabled = True
            
        return jsonify({
            'success': True,
            'email': RECIPIENT_EMAIL,
            'email_enabled': email_alerts_enabled,
            'message': f'Email notifications will be sent to {RECIPIENT_EMAIL}'
        })
    except Exception as e:
        print(f"Error setting recipient email: {e}")
        return jsonify({'success': False, 'error': f'Error setting recipient email: {str(e)}'}), 500

@app.route('/toggle_email_alerts', methods=['POST'])
def toggle_email_alerts():
    """Toggle email alerts on/off."""
    global email_alerts_enabled
    
    # Check if recipient email is set
    if not RECIPIENT_EMAIL:
        return jsonify({
            'success': False,
            'enabled': False,
            'error': 'Email alerts cannot be enabled: Missing recipient email'
        }), 400
    
    # Toggle email alerts
    email_alerts_enabled = not email_alerts_enabled
    
    return jsonify({
        'success': True,
        'enabled': email_alerts_enabled,
        'message': f'Email alerts turned {"ON" if email_alerts_enabled else "OFF"}'
    })

@app.route('/get_email_config', methods=['GET'])
def get_email_config():
    """Get current email configuration status."""
    
    return jsonify({
        'enabled': email_alerts_enabled,
        'configured': bool(RECIPIENT_EMAIL),
        'recipient_email': RECIPIENT_EMAIL
    })

@app.route('/test_email', methods=['POST'])
def test_email():
    """Send a test email to verify the email integration."""
    global RECIPIENT_EMAIL
    
    print("Test email endpoint called")
    
    # Verify recipient email is set
    if not RECIPIENT_EMAIL:
        return jsonify({
            'success': False,
            'error': 'No recipient email set. Please configure your email first.'
        }), 400
    
    # Format timestamp for the test message
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    subject = "Test Alert from Face Recognition System"
    test_message = f"🔔 TEST ALERT: This is a test message from your Face Recognition System at {timestamp}"
    
    try:
        # Bypass message cooldown for test messages
        global last_message_time
        last_message_time = 0
        
        # Send the test email
        if send_email_alert(subject, test_message):
            return jsonify({
                'success': True,
                'message': f'Test email sent successfully to {RECIPIENT_EMAIL}'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to send test email. Please check server logs for details.'
            }), 500
            
    except Exception as e:
        error_message = str(e)
        print(f"Error sending test email: {error_message}")
        
        return jsonify({
            'success': False,
            'error': f'Error sending test email: {error_message}'
        }), 500

if __name__ == '__main__':
    app.run(debug=True) 