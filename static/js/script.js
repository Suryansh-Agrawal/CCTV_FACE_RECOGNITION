document.addEventListener('DOMContentLoaded', () => {
    const videoElement = document.querySelector('.video-container img');
    const statusElement = document.getElementById('status');
    const captureBtn = document.getElementById('capture-btn');
    const addFaceBtn = document.getElementById('add-face-btn');
    const faceNameInput = document.getElementById('face-name');
    const captureCanvas = document.getElementById('capture-canvas');
    const capturedImageContainer = document.getElementById('captured-image-container');
    const addFaceStatus = document.getElementById('add-face-status');
    const knownFacesList = document.getElementById('known-faces-list');
    const toggleRecognitionBtn = document.getElementById('toggle-recognition-btn');
    
    // Schedule UI elements
    const scheduleBtn = document.getElementById('schedule-btn');
    const schedulePanel = document.getElementById('schedule-panel');
    const startTimeInput = document.getElementById('start-time');
    const endTimeInput = document.getElementById('end-time');
    const setScheduleBtn = document.getElementById('set-schedule-btn');
    const cancelScheduleBtn = document.getElementById('cancel-schedule-btn');
    const scheduleStatus = document.getElementById('schedule-status');
    
    // Email notification UI elements
    const emailBtn = document.getElementById('email-btn');
    const emailPanel = document.getElementById('email-panel');
    const recipientEmailInput = document.getElementById('recipient-email');
    const saveEmailBtn = document.getElementById('save-email-btn');
    const toggleEmailBtn = document.getElementById('toggle-email-btn');
    const emailStatus = document.getElementById('email-status');
    const testEmailBtn = document.getElementById('test-email-btn');

    // SMS notification UI elements
    const smsBtn = document.getElementById('sms-btn');
    const smsPanel = document.getElementById('sms-panel');
    const recipientPhoneInput = document.getElementById('recipient-phone');
    const savePhoneBtn = document.getElementById('save-phone-btn');
    const toggleSmsBtn = document.getElementById('toggle-sms-btn');
    const smsStatus = document.getElementById('sms-status');
    const testSmsBtn = document.getElementById('test-sms-btn');
    
    let faceDetected = false;
    let checkInterval = null;
    let capturedImageData = null;
    let recognitionEnabled = true; // Default state
    let isScheduled = false;
    let emailAlertsEnabled = false;
    let smsAlertsEnabled = false;
    
    // Function to update the status message
    function updateStatus() {
        if (videoElement.complete && videoElement.naturalHeight !== 0) {
            if (!faceDetected) {
                statusElement.textContent = "Face detected!";
                statusElement.style.color = "#27ae60";
                faceDetected = true;
            }
        } else {
            statusElement.textContent = "No video feed available";
            statusElement.style.color = "#e74c3c";
        }
    }
    
    // Check status periodically
    checkInterval = setInterval(updateStatus, 1000);
    
    // Load known faces
    loadKnownFaces();
    
    // Check if there's an active schedule
    checkScheduleStatus();
    
    // Check Email configuration
    checkEmailConfig();
    
    // Check SMS configuration
    checkSmsConfig();
    
    // Toggle recognition button click event
    toggleRecognitionBtn.addEventListener('click', () => {
        toggleFaceRecognition();
    });
    
    // Schedule button click event
    scheduleBtn.addEventListener('click', () => {
        toggleSchedulePanel();
    });
    
    // Email button click event
    emailBtn.addEventListener('click', () => {
        toggleEmailPanel();
    });
    
    // Set schedule button click event
    setScheduleBtn.addEventListener('click', () => {
        setSchedule();
    });
    
    // Cancel schedule button click event
    cancelScheduleBtn.addEventListener('click', () => {
        cancelSchedule();
    });
    
    // Save email button click event
    saveEmailBtn.addEventListener('click', () => {
        saveEmail();
    });
    
    // Toggle Email alerts button click event
    toggleEmailBtn.addEventListener('click', () => {
        toggleEmailAlerts();
    });
    
    // Test Email button click event
    testEmailBtn.addEventListener('click', () => {
        sendTestEmail();
    });
    
    // SMS button click event
    if (smsBtn) {
        smsBtn.addEventListener('click', () => {
            toggleSmsPanel();
        });
    }
    
    // Save phone button click event
    if (savePhoneBtn) {
        savePhoneBtn.addEventListener('click', () => {
            savePhoneNumber();
        });
    }
    
    // Toggle SMS alerts button click event
    if (toggleSmsBtn) {
        toggleSmsBtn.addEventListener('click', () => {
            toggleSmsAlerts();
        });
    }
    
    // Test SMS button click event
    if (testSmsBtn) {
        testSmsBtn.addEventListener('click', () => {
            sendTestSms();
        });
    }
    
    // Capture button click event
    captureBtn.addEventListener('click', () => {
        captureImage();
    });
    
    // Add face button click event
    addFaceBtn.addEventListener('click', () => {
        addFace();
    });
    
    // Name input validation
    faceNameInput.addEventListener('input', validateName);
    
    // Function to toggle schedule panel visibility
    function toggleSchedulePanel() {
        if (schedulePanel.style.display === 'none') {
            schedulePanel.style.display = 'block';
            // Hide Email and SMS panels if they're open
            emailPanel.style.display = 'none';
            smsPanel.style.display = 'none';
            loadDefaultTimes();
        } else {
            schedulePanel.style.display = 'none';
        }
    }
    
    // Function to toggle Email panel visibility
    function toggleEmailPanel() {
        if (emailPanel.style.display === 'none') {
            emailPanel.style.display = 'block';
            // Hide schedule panel if it's open
            schedulePanel.style.display = 'none';
        } else {
            emailPanel.style.display = 'none';
        }
    }
    
    // Function to toggle SMS panel visibility
    function toggleSmsPanel() {
        if (smsPanel.style.display === 'none') {
            smsPanel.style.display = 'block';
            // Hide other panels
            schedulePanel.style.display = 'none';
            emailPanel.style.display = 'none';
        } else {
            smsPanel.style.display = 'none';
        }
    }
    
    // Function to load default times (current time + 1 hour)
    function loadDefaultTimes() {
        const now = new Date();
        
        // Set default start time to current time
        let hours = now.getHours();
        let minutes = now.getMinutes();
        startTimeInput.value = `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}`;
        
        // Set default end time to one hour from now
        hours = (hours + 1) % 24;
        endTimeInput.value = `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}`;
    }
    
    // Function to check if there's an active schedule
    function checkScheduleStatus() {
        fetch('/get_schedule')
            .then(response => response.json())
            .then(data => {
                if (data.scheduled) {
                    isScheduled = true;
                    startTimeInput.value = data.start_time;
                    endTimeInput.value = data.end_time;
                    
                    updateScheduleUI(true);
                    showScheduleStatus(`Recognition scheduled from ${data.start_time} to ${data.end_time}`, 'success');
                } else {
                    isScheduled = false;
                    updateScheduleUI(false);
                }
            })
            .catch(error => {
                console.error('Error checking schedule status:', error);
            });
    }
    
    // Function to check Email configuration
    function checkEmailConfig() {
        fetch('/get_email_config')
            .then(response => response.json())
            .then(data => {
                // Update recipient email if set
                if (data.recipient_email) {
                    recipientEmailInput.value = data.recipient_email;
                }
                
                // Update Email alerts status
                emailAlertsEnabled = data.enabled;
                const isConfigured = data.configured;
                updateEmailUI(isConfigured, data.enabled);
                
                if (isConfigured) {
                    showEmailStatus('Email notifications configured', 'success');
                }
            })
            .catch(error => {
                console.error('Error checking Email configuration:', error);
            });
    }
    
    // Function to save recipient email
    function saveEmail() {
        const email = recipientEmailInput.value.trim();
        
        // Basic validation
        if (!email || !isValidEmail(email)) {
            showEmailStatus('Please enter a valid email address', 'error');
            return;
        }
        
        // Show loading status
        showEmailStatus('Saving email...', '');
        
        // Send data to server
        fetch('/set_email', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                email: email
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                updateEmailUI(true, data.email_enabled);
                showEmailStatus(data.message, 'success');
            } else {
                showEmailStatus(data.error, 'error');
            }
        })
        .catch(error => {
            console.error('Error saving email:', error);
            showEmailStatus('Error saving email', 'error');
        });
    }
    
    // Function to validate email format
    function isValidEmail(email) {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return emailRegex.test(email);
    }
    
    // Function to toggle Email alerts
    function toggleEmailAlerts() {
        fetch('/toggle_email_alerts', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                emailAlertsEnabled = data.enabled;
                updateEmailAlertToggle(emailAlertsEnabled);
                showEmailStatus(data.message, 'success');
            } else {
                showEmailStatus(data.error, 'error');
            }
        })
        .catch(error => {
            console.error('Error toggling Email alerts:', error);
            showEmailStatus('Error toggling Email alerts', 'error');
        });
    }
    
    // Function to update Email UI based on configuration
    function updateEmailUI(configured, enabled) {
        // Update toggle button state
        toggleEmailBtn.disabled = !configured;
        updateEmailAlertToggle(enabled);
        
        // Update the main Email button appearance
        if (configured) {
            emailBtn.classList.add('configured');
            if (enabled) {
                emailBtn.classList.add('active');
            } else {
                emailBtn.classList.remove('active');
            }
        } else {
            emailBtn.classList.remove('configured', 'active');
        }
    }
    
    // Function to update Email alert toggle button
    function updateEmailAlertToggle(enabled) {
        if (enabled) {
            toggleEmailBtn.classList.remove('inactive');
            toggleEmailBtn.classList.add('active');
            toggleEmailBtn.querySelector('.status-text').textContent = 'Email Alerts: ON';
        } else {
            toggleEmailBtn.classList.remove('active');
            toggleEmailBtn.classList.add('inactive');
            toggleEmailBtn.querySelector('.status-text').textContent = 'Email Alerts: OFF';
        }
    }
    
    // Function to show Email status messages
    function showEmailStatus(message, type) {
        emailStatus.textContent = message;
        
        // Remove all classes
        emailStatus.classList.remove('success-message', 'error-message');
        
        // Add appropriate class based on message type
        if (type === 'success') {
            emailStatus.classList.add('success-message');
        } else if (type === 'error') {
            emailStatus.classList.add('error-message');
        }
    }
    
    // Function to send a test Email
    function sendTestEmail() {
        // Show loading status
        showEmailStatus('Sending test email...', '');
        
        fetch('/test_email', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showEmailStatus(data.message, 'success');
            } else {
                showEmailStatus(data.error, 'error');
            }
        })
        .catch(error => {
            console.error('Error sending test email:', error);
            showEmailStatus('Error sending test email. Check console for details.', 'error');
        });
    }
    
    // Function to set a schedule
    function setSchedule() {
        const startTime = startTimeInput.value;
        const endTime = endTimeInput.value;
        
        if (!startTime || !endTime) {
            showScheduleStatus('Please set both start and end times', 'error');
            return;
        }
        
        fetch('/schedule_recognition', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                start_time: startTime,
                end_time: endTime
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                isScheduled = true;
                updateScheduleUI(true);
                showScheduleStatus(data.message, 'success');
            } else {
                showScheduleStatus(data.error, 'error');
            }
        })
        .catch(error => {
            console.error('Error setting schedule:', error);
            showScheduleStatus('Error setting schedule', 'error');
        });
    }
    
    // Function to cancel a schedule
    function cancelSchedule() {
        fetch('/cancel_schedule', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                isScheduled = false;
                updateScheduleUI(false);
                showScheduleStatus(data.message, 'success');
            } else {
                showScheduleStatus(data.error, 'error');
            }
        })
        .catch(error => {
            console.error('Error canceling schedule:', error);
            showScheduleStatus('Error canceling schedule', 'error');
        });
    }
    
    // Function to update the schedule UI based on scheduled state
    function updateScheduleUI(scheduled) {
        if (scheduled) {
            scheduleBtn.textContent = 'Scheduled';
            scheduleBtn.classList.add('active');
            cancelScheduleBtn.disabled = false;
            setScheduleBtn.textContent = 'Update Schedule';
        } else {
            scheduleBtn.textContent = 'Schedule Recognition';
            scheduleBtn.classList.remove('active');
            cancelScheduleBtn.disabled = true;
            setScheduleBtn.textContent = 'Set Schedule';
            clearScheduleStatus();
        }
    }
    
    // Function to show schedule status messages
    function showScheduleStatus(message, type) {
        scheduleStatus.textContent = message;
        
        // Remove all classes
        scheduleStatus.classList.remove('success-message', 'error-message');
        
        // Add appropriate class based on message type
        if (type === 'success') {
            scheduleStatus.classList.add('success-message');
        } else if (type === 'error') {
            scheduleStatus.classList.add('error-message');
        }
    }
    
    // Function to clear schedule status
    function clearScheduleStatus() {
        scheduleStatus.textContent = '';
        scheduleStatus.classList.remove('success-message', 'error-message');
    }
    
    // Function to toggle face recognition
    function toggleFaceRecognition() {
        fetch('/toggle_recognition', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                recognitionEnabled = data.enabled;
                isScheduled = data.scheduled;
                updateToggleButton();
                updateScheduleUI(isScheduled);
                showStatus(data.message, 'success');
            }
        })
        .catch(error => {
            console.error('Error toggling recognition:', error);
            showStatus('Error toggling face recognition', 'error');
        });
    }
    
    // Function to update toggle button appearance
    function updateToggleButton() {
        if (recognitionEnabled) {
            toggleRecognitionBtn.classList.remove('inactive');
            toggleRecognitionBtn.classList.add('active');
            toggleRecognitionBtn.querySelector('.status-text').textContent = 'Recognition: ON';
        } else {
            toggleRecognitionBtn.classList.remove('active');
            toggleRecognitionBtn.classList.add('inactive');
            toggleRecognitionBtn.querySelector('.status-text').textContent = 'Recognition: OFF';
        }
    }
    
    // Function to capture the current frame from video
    function captureImage() {
        if (!videoElement.complete || videoElement.naturalHeight === 0) {
            showStatus('Cannot capture image: No video feed available', 'error');
            return;
        }
        
        const ctx = captureCanvas.getContext('2d');
        
        // Set canvas dimensions to match the aspect ratio of the video
        const aspectRatio = videoElement.naturalWidth / videoElement.naturalHeight;
        captureCanvas.width = 320;
        captureCanvas.height = captureCanvas.width / aspectRatio;
        
        // Draw the current frame onto the canvas
        ctx.drawImage(videoElement, 0, 0, captureCanvas.width, captureCanvas.height);
        
        // Get the image data as base64
        capturedImageData = captureCanvas.toDataURL('image/jpeg');
        
        // Show the captured image
        capturedImageContainer.style.display = 'block';
        
        // Enable the add face button if name is valid
        validateName();
        
        showStatus('Image captured! Enter a name and click "Add Face"', 'success');
    }
    
    // Function to validate the name input
    function validateName() {
        const name = faceNameInput.value.trim();
        
        if (name && capturedImageData) {
            addFaceBtn.disabled = false;
        } else {
            addFaceBtn.disabled = true;
        }
    }
    
    // Function to add a face to the known faces
    function addFace() {
        const name = faceNameInput.value.trim();
        
        if (!name) {
            showStatus('Please enter a name', 'error');
            return;
        }
        
        if (!capturedImageData) {
            showStatus('Please capture an image first', 'error');
            return;
        }
        
        // Disable button to prevent multiple submissions
        addFaceBtn.disabled = true;
        
        // Show loading status
        showStatus('Adding face...', '');
        
        // Send data to server
        fetch('/add_face', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                name: name,
                image: capturedImageData
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showStatus(data.message, 'success');
                
                // Reset the form
                faceNameInput.value = '';
                capturedImageData = null;
                capturedImageContainer.style.display = 'none';
                
                // Reload known faces
                loadKnownFaces();
            } else {
                showStatus(data.error, 'error');
                addFaceBtn.disabled = false;
            }
        })
        .catch(error => {
            showStatus('Error adding face: ' + error.message, 'error');
            addFaceBtn.disabled = false;
        });
    }
    
    // Function to show status messages
    function showStatus(message, type) {
        addFaceStatus.textContent = message;
        
        // Remove all classes
        addFaceStatus.classList.remove('success-message', 'error-message');
        
        // Add appropriate class based on message type
        if (type === 'success') {
            addFaceStatus.classList.add('success-message');
        } else if (type === 'error') {
            addFaceStatus.classList.add('error-message');
        }
    }
    
    // Function to load known faces from the server
    function loadKnownFaces() {
        fetch('/known_faces')
            .then(response => response.json())
            .then(data => {
                if (data.faces && data.faces.length > 0) {
                    const facesList = data.faces.map(face => 
                        `<div class="face-item">${face.name}</div>`
                    ).join('');
                    
                    knownFacesList.innerHTML = facesList;
                } else {
                    knownFacesList.innerHTML = '<p>No known faces found</p>';
                }
            })
            .catch(error => {
                knownFacesList.innerHTML = '<p>Error loading known faces</p>';
                console.error('Error loading known faces:', error);
            });
    }
    
    // Function to check SMS configuration
    function checkSmsConfig() {
        fetch('/get_sms_config')
            .then(response => response.json())
            .then(data => {
                // Update recipient phone if set
                if (data.recipient_phone) {
                    recipientPhoneInput.value = data.recipient_phone;
                }
                
                // Update SMS alerts status
                smsAlertsEnabled = data.enabled;
                const isConfigured = data.configured;
                updateSmsUI(isConfigured, data.enabled);
                
                if (isConfigured) {
                    showSmsStatus('SMS notifications configured', 'success');
                }
            })
            .catch(error => {
                console.error('Error checking SMS configuration:', error);
            });
    }
    
    // Function to save recipient phone number
    function savePhoneNumber() {
        const phone = recipientPhoneInput.value.trim();
        
        // Basic validation - Indian phone number (10 digits)
        if (!phone || !isValidIndianPhone(phone)) {
            showSmsStatus('Please enter a valid 10-digit Indian mobile number', 'error');
            return;
        }
        
        // Show loading status
        showSmsStatus('Saving phone number...', '');
        
        // Send data to server
        fetch('/set_sms', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                phone: phone
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                updateSmsUI(true, data.sms_enabled);
                showSmsStatus(data.message, 'success');
            } else {
                showSmsStatus(data.error, 'error');
            }
        })
        .catch(error => {
            console.error('Error saving phone number:', error);
            showSmsStatus('Error saving phone number', 'error');
        });
    }
    
    // Function to validate Indian phone number format
    function isValidIndianPhone(phone) {
        // Check if it's a 10-digit number
        const phoneRegex = /^[6-9]\d{9}$/;
        return phoneRegex.test(phone);
    }
    
    // Function to toggle SMS alerts
    function toggleSmsAlerts() {
        fetch('/toggle_sms_alerts', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                smsAlertsEnabled = data.enabled;
                updateSmsAlertToggle(data.enabled);
                showSmsStatus(data.message, 'success');
            } else {
                showSmsStatus(data.error, 'error');
            }
        })
        .catch(error => {
            console.error('Error toggling SMS alerts:', error);
            showSmsStatus('Error toggling SMS alerts', 'error');
        });
    }
    
    // Function to update SMS UI
    function updateSmsUI(configured, enabled) {
        // Update test button and toggle button visibility
        if (testSmsBtn) {
            testSmsBtn.style.display = configured ? 'inline-block' : 'none';
        }
        
        if (toggleSmsBtn) {
            toggleSmsBtn.style.display = configured ? 'inline-block' : 'none';
            updateSmsAlertToggle(enabled);
        }
        
        // Update phone input and save button
        if (recipientPhoneInput) {
            recipientPhoneInput.disabled = false;
        }
        
        if (savePhoneBtn) {
            savePhoneBtn.disabled = false;
        }
    }
    
    // Function to update SMS alert toggle button
    function updateSmsAlertToggle(enabled) {
        if (toggleSmsBtn) {
            toggleSmsBtn.textContent = enabled ? 'Disable SMS Alerts' : 'Enable SMS Alerts';
            toggleSmsBtn.classList.toggle('active', enabled);
        }
    }
    
    // Function to show SMS status
    function showSmsStatus(message, type) {
        if (smsStatus) {
            smsStatus.textContent = message;
            
            // Reset classes
            smsStatus.className = 'status';
            
            // Add appropriate class based on type
            if (type) {
                smsStatus.classList.add(type);
            }
            
            smsStatus.style.display = 'block';
        }
    }
    
    // Function to send test SMS
    function sendTestSms() {
        showSmsStatus('Sending test SMS...', '');
        
        fetch('/test_sms', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showSmsStatus(data.message, 'success');
            } else {
                showSmsStatus(data.error, 'error');
            }
        })
        .catch(error => {
            console.error('Error sending test SMS:', error);
            showSmsStatus('Error sending test SMS', 'error');
        });
    }
    
    // Clean up interval on page unload
    window.addEventListener('beforeunload', () => {
        if (checkInterval) {
            clearInterval(checkInterval);
        }
    });
}); 