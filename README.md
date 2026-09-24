# Driver_Safe
Driver Cognitive Load & Drowsiness Detection System — a mobile-based intelligent safety application that uses real-time computer vision and behavioral analysis to detect driver drowsiness and cognitive overload, trigger instant alerts, and notify emergency contacts and nearby hospitals during critical situations.

🛡️ Drive Safe - AI Drowsiness Detection System
Drive Safe is a life-saving Flutter application designed to prevent road accidents caused by driver fatigue. It uses Artificial Intelligence (Google ML Kit) to monitor the driver's eyes in real-time and triggers alarms if drowsiness is detected.

If the driver remains unresponsive, the app automatically sends an Emergency Telegram Alert containing the driver's Live GPS Location and a list of Nearby Hospitals to a pre-set emergency contact.

🚀 Key Features
👁️ Real-Time Eye Tracking: Uses Google ML Kit Face Detection to calculate Eye Aspect Ratio (EAR) and eye-open probability.

⏱️ Multi-Stage Alerts:
Microsleep Warning (0.5s): Yellow UI warning for short blinks.
Drowsiness Alarm (1.0s): Loud audio alarm and Red UI screen.
Emergency Trigger (5.0s): Automatically contacts emergency services.

🆘 Automated Telegram SOS: Sends a critical alert message via a Telegram Bot including:
Driver Name & Vehicle Details.
Live GPS Coordinates (Google Maps Link).
Nearby Hospitals (Fetched via OpenStreetMap/Overpass API).

📱 Device Compatibility: Includes a custom NV21 Image Converter to support cameras on specific Android devices (Vivo, Samsung, etc.) that use non-standard YUV formats.

🎨 Professional UI: Clean, high-contrast "Medical Blue" interface for visibility during day and night driving.

🛠️ Tech Stack
Framework: Flutter (Dart)
Face Detection: google_mlkit_face_detection
Camera: camera
Audio: audioplayers
Networking: http (for Telegram & Overpass API)
Location: geolocator

⚙️ Installation & Setup
1. Prerequisites
Flutter SDK installed.
VS Code or Android Studio.
Physical Android Device (Simulators cannot test the camera efficiently).

2. Clone the Repository
Bash
git clone https://github.com/your-username/drive-safe.git
cd drive-safe
3. Install Dependencies
Bash
flutter pub get
4. Configuration
A. Telegram Bot Setup

Open lib/main.dart.

Find the variable telegramBotToken.

Replace it with your own bot token from @BotFather.

Dart
final String telegramBotToken = "YOUR_NEW_TOKEN_HERE";
B. Permissions Ensure your android/app/src/main/AndroidManifest.xml has the following permissions:

XML
<uses-permission android:name="android.permission.CAMERA"/>
<uses-permission android:name="android.permission.ACCESS_FINE_LOCATION"/>
<uses-permission android:name="android.permission.ACCESS_COARSE_LOCATION"/>
<uses-permission android:name="android.permission.INTERNET"/>
C. Assets Ensure you have an alarm.mp3 file in the assets/ folder and it is registered in pubspec.yaml:

YAML
flutter:
  assets:
    - assets/alarm.mp3
5. Run the App
Connect your phone and run:

Bash
flutter run
🧠 How It Works
Input: The app captures a video stream from the front camera.

Processing:

It converts the raw camera image (YUV/NV21) into a format ML Kit can read.
ML Kit detects the face and identifies 6 landmarks per eye.

Logic:

It calculates the EAR (Eye Aspect Ratio). If EAR < 0.25, the eye is considered "Closed".
It starts a timer.

Triggers:

> 500ms: Warning state (Microsleep).
> 1000ms: Alarm state (Audio plays).
> 5000ms: Emergency state (Telegram API called with GPS data).

🤝 Contributing
Contributions are welcome!
Fork the Project.
Create your Feature Branch (git checkout -b feature/AmazingFeature).
Commit your Changes (git commit -m 'Add some AmazingFeature').
Push to the Branch (git push origin feature/AmazingFeature).
Open a Pull Request.

📄 License
Distributed under the MIT License. See LICENSE for more information.

📞 Contact
Aniket Saini

GitHub: anikettt-cd

Email:  sainianiket751@gmail.com

⚠️ Disclaimer
This application is a driver assistance tool. It is not a substitute for rest and responsible driving habits. The developers are not liable for any accidents or failures in the alert system.
