# WakeDrive Server

This is the Flask backend for the WakeDrive Flutter application. It provides Session Management, Event Logging, Face Verification, and a Web Dashboard.

## Installation

1. Make sure you have Python 3.8+ installed.
2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Running the Server

Run the Flask server:
```bash
python app.py
```

- The server will start on `http://localhost:5000` or `http://0.0.0.0:5000` (accessible via your local IP address).
- The dashboard is accessible at `http://localhost:5000/dashboard`.
- Flask-CORS is enabled so the Flutter app can communicate with the APIs.

## Note for Flutter App
In `lib/main.dart`, ensure that `flaskBaseUrl` is updated to the local IP address of the machine running this server.
