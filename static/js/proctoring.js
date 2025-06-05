// Proctoring System JavaScript

class ProctorSystem {
    constructor() {
        this.mediaStream = null;
        this.isActive = false;
        this.violations = [];
        
        this.init();
    }

    init() {
        this.setupEventListeners();
    }

    setupEventListeners() {
        const startButton = document.getElementById('startProctoring');
        if (startButton) {
            startButton.addEventListener('click', () => this.enableProctoring());
        }
    }

    async enableProctoring() {
        try {
            // Request camera and microphone access
            this.mediaStream = await navigator.mediaDevices.getUserMedia({
                video: {
                    width: { ideal: 640 },
                    height: { ideal: 480 },
                    facingMode: 'user'
                },
                audio: true
            });

            // Set up camera feeds
            const cameraFeed = document.getElementById('cameraFeed');
            const miniCameraFeed = document.getElementById('miniCameraFeed');
            
            if (cameraFeed) {
                cameraFeed.srcObject = this.mediaStream;
            }
            
            if (miniCameraFeed) {
                miniCameraFeed.srcObject = this.mediaStream;
            }

            this.isActive = true;
            
            // Show success message
            Utils.showNotification('Proctoring enabled successfully. Starting assessment...', 'success');
            
            // Start assessment after brief delay
            setTimeout(() => {
                if (typeof startAssessment === 'function') {
                    startAssessment();
                }
            }, 2000);

        } catch (error) {
            console.error('Error accessing camera/microphone:', error);
            this.handleProctoringError(error);
        }
    }

    handleProctoringError(error) {
        let errorMessage = 'Unable to access camera and microphone. ';
        
        if (error.name === 'NotAllowedError') {
            errorMessage += 'Please grant camera and microphone permissions and try again.';
        } else if (error.name === 'NotFoundError') {
            errorMessage += 'No camera or microphone found on this device.';
        } else if (error.name === 'NotReadableError') {
            errorMessage += 'Camera or microphone is being used by another application.';
        } else {
            errorMessage += 'Please check your device settings and try again.';
        }

        Utils.showNotification(errorMessage, 'danger');
        
        // Show fallback options
        this.showFallbackOptions();
    }

    showFallbackOptions() {
        const proctoringSetup = document.getElementById('proctoringSetup');
        const cardBody = proctoringSetup.querySelector('.card-body');
        
        cardBody.innerHTML = `
            <div class="alert alert-danger">
                <h5><i class="fas fa-exclamation-triangle"></i> Camera Access Required</h5>
                <p>This assessment requires camera and microphone access for proctoring purposes.</p>
                
                <h6>Troubleshooting Steps:</h6>
                <ol>
                    <li>Click the camera icon in your browser's address bar</li>
                    <li>Select "Allow" for both camera and microphone</li>
                    <li>Refresh the page and try again</li>
                    <li>Ensure no other applications are using your camera</li>
                </ol>
            </div>
            
            <div class="text-center">
                <button id="retryProctoring" class="btn btn-primary btn-lg me-2">
                    <i class="fas fa-redo"></i>
                    Try Again
                </button>
                <a href="${window.location.origin}/dashboard" class="btn btn-outline-secondary btn-lg">
                    <i class="fas fa-arrow-left"></i>
                    Back to Dashboard
                </a>
            </div>
        `;
        
        // Add retry functionality
        document.getElementById('retryProctoring').addEventListener('click', () => {
            location.reload();
        });
    }

    stopProctoring() {
        if (this.mediaStream) {
            this.mediaStream.getTracks().forEach(track => track.stop());
            this.mediaStream = null;
        }
        this.isActive = false;
    }

    recordViolation(type, description) {
        const violation = {
            type: type,
            description: description,
            timestamp: new Date().toISOString()
        };
        
        this.violations.push(violation);
        console.warn('Proctoring violation recorded:', violation);
    }

    // Additional monitoring methods
    startFaceDetection() {
        // Placeholder for face detection implementation
        // This would integrate with face detection libraries like face-api.js
        console.log('Face detection monitoring started');
    }

    startAudioMonitoring() {
        // Placeholder for audio level monitoring
        // This would monitor for unusual audio patterns
        console.log('Audio monitoring started');
    }

    // Cleanup method
    cleanup() {
        this.stopProctoring();
        this.violations = [];
    }
}

// Initialize proctoring system
document.addEventListener('DOMContentLoaded', function() {
    if (document.getElementById('proctoringSetup')) {
        window.proctorSystem = new ProctorSystem();
    }
});

// Cleanup on page unload
window.addEventListener('beforeunload', function() {
    if (window.proctorSystem) {
        window.proctorSystem.cleanup();
    }
});

// Export for external use
window.ProctorSystem = ProctorSystem;
