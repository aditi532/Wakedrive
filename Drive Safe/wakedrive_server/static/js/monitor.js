const videoElement = document.getElementById('input_video');
const canvasElement = document.getElementById('output_canvas');
const canvasCtx = canvasElement.getContext('2d');
const videoWrapper = document.getElementById('video-wrapper');
const statusText = document.getElementById('status-text');
const statusDot = document.getElementById('status-dot');
const alarmAudio = document.getElementById('alarm-audio');
const endSessionBtn = document.getElementById('end-session-btn');

const sessionId = localStorage.getItem('current_session_id');

// Configuration
let EAR_THRESHOLD = 0.25; // Will be calibrated dynamically
const MICROSLEEP_MS = 500;
const DROWSINESS_MS = 1000;
const YAWN_MS = 2000;
const HEAD_DROP_MS = 1500;
const MAR_THRESHOLD = 0.5;
const PITCH_THRESHOLD = 0.7; // Ratio of (Nose to Chin) / (Nose to Forehead)

let isCalibrated = false;
let calibrationFrames = 0;
let earSum = 0;

let eyeClosedStartTime = null;
let yawnStartTime = null;
let headDropStartTime = null;

let currentState = 'alert'; // alert, warning, danger
let hasLoggedMicrosleep = false;
let hasLoggedDrowsy = false;
let hasLoggedEmergency = false;
let hasLoggedYawn = false;
let hasLoggedHeadDrop = false;

// GPS Tracking
let currentLat = null;
let currentLng = null;

if ("geolocation" in navigator) {
    // Fire immediately to get a fix before the first drowsy event
    navigator.geolocation.getCurrentPosition((position) => {
        currentLat = position.coords.latitude;
        currentLng = position.coords.longitude;
        console.log(`GPS ready: ${currentLat}, ${currentLng}`);
    }, (err) => console.warn("GPS initial fix failed:", err.message),
    { enableHighAccuracy: true, timeout: 10000 });

    // Keep updating during the trip
    navigator.geolocation.watchPosition((position) => {
        currentLat = position.coords.latitude;
        currentLng = position.coords.longitude;
    }, (err) => console.warn("GPS watch error:", err.message),
    { enableHighAccuracy: true, maximumAge: 5000, timeout: 10000 });
}

// MediaPipe Face Mesh Landmark indices for eyes
// Right eye
const RIGHT_EYE = [362, 385, 387, 263, 373, 380];
// Left eye
const LEFT_EYE = [33, 160, 158, 133, 153, 144];

// Mouth
const MOUTH_TOP = 13;
const MOUTH_BOTTOM = 14;
const MOUTH_LEFT = 78;
const MOUTH_RIGHT = 308;

// Head Pitch
const NOSE = 1;
const CHIN = 152;
const FOREHEAD = 10;

function calculateEAR(landmarks, eyeIndices) {
    const p1 = landmarks[eyeIndices[0]];
    const p2 = landmarks[eyeIndices[1]];
    const p3 = landmarks[eyeIndices[2]];
    const p4 = landmarks[eyeIndices[3]];
    const p5 = landmarks[eyeIndices[4]];
    const p6 = landmarks[eyeIndices[5]];

    // Euclidean distance
    const dist = (pt1, pt2) => Math.sqrt(Math.pow(pt1.x - pt2.x, 2) + Math.pow(pt1.y - pt2.y, 2));

    const v1 = dist(p2, p6);
    const v2 = dist(p3, p5);
    const h = dist(p1, p4);

    return (v1 + v2) / (2.0 * h);
}

function calculateMAR(landmarks) {
    const top = landmarks[MOUTH_TOP];
    const bottom = landmarks[MOUTH_BOTTOM];
    const left = landmarks[MOUTH_LEFT];
    const right = landmarks[MOUTH_RIGHT];

    const dist = (pt1, pt2) => Math.sqrt(Math.pow(pt1.x - pt2.x, 2) + Math.pow(pt1.y - pt2.y, 2));

    const v = dist(top, bottom);
    const h = dist(left, right);
    return v / h;
}

function calculateHeadPitch(landmarks) {
    const nose = landmarks[NOSE];
    const chin = landmarks[CHIN];
    const forehead = landmarks[FOREHEAD];

    const dist = (pt1, pt2) => Math.sqrt(Math.pow(pt1.x - pt2.x, 2) + Math.pow(pt1.y - pt2.y, 2));

    const noseToChin = dist(nose, chin);
    const noseToForehead = dist(nose, forehead);
    
    // As the head drops, the chin comes closer to the nose in 2D projection
    return noseToChin / noseToForehead;
}

function updateUI(state, customMessage = null) {
    const targetText = customMessage || (state === 'alert' ? 'Driver Alert' : state === 'warning' ? 'Microsleep Detected' : 'DANGER: DROWSY');
    
    if (currentState === state && statusText.textContent === targetText) return;
    
    currentState = state;
    videoWrapper.className = 'video-wrapper ' + (state === 'alert' ? '' : state);
    statusDot.className = 'status-dot ' + (state === 'alert' ? '' : state);
    statusText.textContent = targetText;
    
    if (state === 'alert') {
        alarmAudio.pause();
        alarmAudio.currentTime = 0;
    } else if (state === 'warning') {
        // warning does not play audio
    } else if (state === 'danger') {
        alarmAudio.play().catch(e => console.log("Audio play blocked by browser", e));
    }
}

async function logEvent(eventType) {
    if (!sessionId) {
        console.error("No session_id found in localStorage!");
        return;
    }
    
    if (currentLat === null && "geolocation" in navigator) {
        try {
            const pos = await new Promise((resolve, reject) => {
                navigator.geolocation.getCurrentPosition(resolve, reject, {
                    enableHighAccuracy: true,
                    timeout: 2000
                });
            });
            currentLat = pos.coords.latitude;
            currentLng = pos.coords.longitude;
        } catch (err) {
            console.warn("GPS fallback failed:", err.message);
        }
    }
    
    console.log(`Firing event: ${eventType} | GPS: ${currentLat}, ${currentLng}`);
    try {
        const res = await fetch('/api/event/log', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                session_id: parseInt(sessionId),   // ← fix here
                event_type: eventType,
                lat: currentLat,
                lng: currentLng
            })
        });
        if (!res.ok) console.error(`Server error: ${res.status}`);
    } catch(e) {
        console.error("Failed to log event:", e);
    }
}

function onResults(results) {
    canvasCtx.save();
    canvasCtx.clearRect(0, 0, canvasElement.width, canvasElement.height);
    canvasCtx.drawImage(results.image, 0, 0, canvasElement.width, canvasElement.height);

    if (results.multiFaceLandmarks && results.multiFaceLandmarks.length > 0) {
        const landmarks = results.multiFaceLandmarks[0];
        
        // Draw mesh (optional, keeping it minimal)
        drawConnectors(canvasCtx, landmarks, FACEMESH_TESSELATION, {color: '#C0C0C070', lineWidth: 1});

        const leftEAR = calculateEAR(landmarks, LEFT_EYE);
        const rightEAR = calculateEAR(landmarks, RIGHT_EYE);
        const ear = (leftEAR + rightEAR) / 2.0;

        // Dynamic Calibration
        if (!isCalibrated) {
            calibrationFrames++;
            earSum += ear;
            statusText.textContent = `Calibrating... (${calibrationFrames}/60)`;
            if (calibrationFrames >= 60) {
                EAR_THRESHOLD = (earSum / calibrationFrames) * 0.70;
                isCalibrated = true;
                console.log(`Calibration complete. Baseline EAR threshold set to: ${EAR_THRESHOLD}`);
                statusText.textContent = 'Driver Alert';
            }
            canvasCtx.restore();
            return;
        }

        const mar = calculateMAR(landmarks);
        const pitchRatio = calculateHeadPitch(landmarks);
        
        let frameState = 'alert';
        let frameMessage = null;

        // Eye Check
        if (ear < EAR_THRESHOLD) {
            if (!eyeClosedStartTime) {
                eyeClosedStartTime = Date.now();
            } else {
                const closedDuration = Date.now() - eyeClosedStartTime;
                
                if (closedDuration >= 3000) { // 3 seconds = EMERGENCY
                    frameState = 'danger';
                    if (!hasLoggedEmergency) {
                        logEvent('emergency');
                        hasLoggedEmergency = true;
                    }
                } else if (closedDuration >= DROWSINESS_MS) { // 1 second = DROWSY
                    frameState = 'danger';
                    if (!hasLoggedDrowsy) {
                        logEvent('drowsy');
                        hasLoggedDrowsy = true;
                    }
                } else if (closedDuration >= MICROSLEEP_MS) { // 0.5 seconds = MICROSLEEP
                    frameState = 'warning';
                    frameMessage = 'Microsleep Detected';
                    if (!hasLoggedMicrosleep) {
                        logEvent('microsleep');
                        hasLoggedMicrosleep = true;
                    }
                }
            }
        } else {
            // Eyes opened
            eyeClosedStartTime = null;
            hasLoggedMicrosleep = false;
            hasLoggedDrowsy = false;
            hasLoggedEmergency = false;
        }

        // Yawn Check
        if (mar > MAR_THRESHOLD) {
            if (!yawnStartTime) yawnStartTime = Date.now();
            else if (Date.now() - yawnStartTime >= YAWN_MS) {
                if (frameState === 'alert') {
                    frameState = 'warning';
                    frameMessage = 'Yawning Detected';
                }
                if (!hasLoggedYawn) {
                    logEvent('yawn');
                    hasLoggedYawn = true;
                }
            }
        } else {
            yawnStartTime = null;
            hasLoggedYawn = false;
        }
        
        // Head Drop Check
        if (pitchRatio < PITCH_THRESHOLD) {
            if (!headDropStartTime) headDropStartTime = Date.now();
            else if (Date.now() - headDropStartTime >= HEAD_DROP_MS) {
                if (frameState === 'alert') {
                    frameState = 'warning';
                    frameMessage = 'Head Drop Detected';
                }
                if (!hasLoggedHeadDrop) {
                    logEvent('head_drop');
                    hasLoggedHeadDrop = true;
                }
            }
        } else {
            headDropStartTime = null;
            hasLoggedHeadDrop = false;
        }

        // Update UI appropriately based on state
        updateUI(frameState, frameMessage);
    }
    canvasCtx.restore();
}

const faceMesh = new FaceMesh({locateFile: (file) => {
    return `https://cdn.jsdelivr.net/npm/@mediapipe/face_mesh/${file}`;
}});

faceMesh.setOptions({
    maxNumFaces: 1,
    refineLandmarks: true,
    minDetectionConfidence: 0.5,
    minTrackingConfidence: 0.5
});

faceMesh.onResults(onResults);

const camera = new Camera(videoElement, {
    onFrame: async () => {
        await faceMesh.send({image: videoElement});
    },
    width: 640,
    height: 480
});

camera.start();

endSessionBtn.addEventListener('click', async () => {
    if (sessionId) {
        await fetch('/api/session/end', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ session_id: sessionId })
        });
        localStorage.removeItem('current_session_id');
    }
    window.location.href = '/dashboard';
});
