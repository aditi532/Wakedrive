# WakeDrive: Cognitive Awareness & Safe Driving Engine

WakeDrive is an intelligent web-based safety application designed to prevent road accidents caused by driver fatigue, microsleeps, and cognitive distraction. Using real-time computer vision (MediaPipe) in the browser, WakeDrive monitors driver behavior and triggers escalating alerts. In the event of a severe emergency, it automatically notifies emergency contacts via Telegram with the driver's live GPS coordinates.

## 🚀 Key Features

- **Real-Time Monitoring**: Uses MediaPipe Face Mesh to continuously track eye aspect ratio (EAR), mouth aspect ratio (MAR), and head pitch.
- **Escalating Alerts**:
  - **Microsleep/Yawn/Head Drop (Warning)**: Visual warnings.
  - **Drowsiness (Alarm)**: Loud audio alarm and visual indicators.
  - **Emergency**: Automatically triggers a Telegram SOS alert.
- **Telegram SOS Integration**: Sends an instant alert with the driver's name, vehicle number, event type, and a live Google Maps GPS link to a pre-configured Telegram Chat ID.
- **Driver Dashboard**: A comprehensive analytics dashboard visualizing total sessions, drowsy events, most dangerous driving times, and historical event graphs.
- **Facial Verification**: Ensures the correct registered driver is operating the vehicle before starting a session.

## 🧠 System Architecture & Flow

### 1. Frontend (Client-Side)
- **Tech Stack**: HTML, CSS, Vanilla JavaScript, MediaPipe (Face Mesh).
- **Functionality**: 
  - Accesses the device webcam and renders the feed.
  - Calculates biometric markers (EAR, MAR, Head Pitch) entirely in the browser for high performance and privacy.
  - Controls local UI states and triggers HTML5 audio alarms.
  - Pings the backend API when specific event thresholds (like 3 seconds of closed eyes) are breached.

### 2. Backend (Server-Side)
- **Tech Stack**: Python, Flask, SQLite.
- **Functionality**:
  - Handles User Authentication and Session tracking.
  - Exposes RESTful APIs (`/api/session/start`, `/api/event/log`, `/api/session/end`) to receive telemetry from the frontend.
  - Manages the SQLite Database (`wakedrive.db`) storing user profiles, historical sessions, and logged events.
  - Executes server-side actions, such as dispatching Telegram HTTP requests via `python-dotenv`.

### Workflow
1. **Auth & Setup**: User logs in and inputs their Telegram Chat ID and vehicle details.
2. **Verification**: User passes a facial verification check.
3. **Monitoring**: The driving session begins. The browser monitors the driver at 30+ FPS.
4. **Event Detection**: If the driver's eyes close for > 1 second (Drowsy) or > 3 seconds (Emergency), an API call is made.
5. **Notification**: The Flask backend receives the API call, looks up the driver's Telegram ID from the database, and sends a formatted SOS message with their GPS coordinates.

---

## ⚙️ How to Run Locally

If you want to run this project on your own machine or contribute to it, follow these steps:

### Prerequisites
- **Python 3.8+** installed on your machine.
- A **Telegram Bot Token** (Create one by talking to [@BotFather](https://t.me/botfather) on Telegram).

### 1. Clone the Repository
```bash
git clone https://github.com/aditi532/Wakedrive.git
cd Wakedrive
```
*(If the server files are nested, navigate into `Drive Safe/wakedrive_server`)*

### 2. Create a Virtual Environment (Recommended)
Creating a virtual environment ensures dependencies don't conflict with other projects on your PC.
```bash
python -m venv venv

# On Windows:
venv\Scripts\activate
# On Mac/Linux:
source venv/bin/activate
```

### 3. Install Dependencies
Install the required Python packages from the requirements file.
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
You need to set up your Telegram Bot token securely.
1. Create a file named `.env` in the same directory as `app.py`.
2. Open the file and add your token like this:
   ```env
   TELEGRAM_BOT_TOKEN="your_token_from_botfather_here"
   ```

### 5. Run the Application
Start the Flask server:
```bash
python app.py
```
By default, the application will be hosted locally. Open your web browser and navigate to:
**`http://localhost:5000`**

### Note on Webcam Access
Because modern browsers restrict webcam usage (getUserMedia) to secure contexts, if you are accessing this server from a different device on your local network (e.g., your phone), you will need to host it over HTTPS or use a tunneling service like [ngrok](https://ngrok.com/). Localhost is automatically treated as a secure context.

---
*Stay awake, stay safe!*
