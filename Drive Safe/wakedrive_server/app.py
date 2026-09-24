import os
import sqlite3
import base64
import numpy as np
import cv2
import mediapipe as mp
from datetime import datetime
from flask import Flask, request, jsonify, render_template, session, flash, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from flask_cors import CORS

app = Flask(__name__)
app.secret_key = 'wakedrive_super_secret_key'
CORS(app)

DB_PATH = "wakedrive.db"
from dotenv import load_dotenv
load_dotenv()
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # Users Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            driver_name TEXT,
            car_number TEXT,
            blood_type TEXT,
            telegram_id TEXT
        )
    ''')
    
    # Add columns if they don't exist (migration)
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN driver_name TEXT")
        cursor.execute("ALTER TABLE users ADD COLUMN car_number TEXT")
        cursor.execute("ALTER TABLE users ADD COLUMN blood_type TEXT")
        cursor.execute("ALTER TABLE users ADD COLUMN telegram_id TEXT")
    except sqlite3.OperationalError:
        pass # Columns already exist
        
    # Sessions Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            driver_name TEXT,
            car_number TEXT,
            blood_type TEXT,
            telegram_id TEXT,
            start_time DATETIME,
            end_time DATETIME,
            duration_minutes REAL
        )
    ''')
    
    # Events Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER,
            event_type TEXT,
            timestamp DATETIME
        )
    ''')
    
    conn.commit()
    conn.close()

# Initialize database
init_db()


# AUTHENTICATION ROUTES
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT id, password_hash FROM users WHERE email = ?", (email,))
        user = cursor.fetchone()
        conn.close()
        
        if user and check_password_hash(user[1], password):
            session['user_id'] = user[0]
            session['email'] = email
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password', 'error')
            
    return render_template('auth.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        try:
            cursor.execute("INSERT INTO users (email, password_hash) VALUES (?, ?)", 
                           (email, generate_password_hash(password)))
            conn.commit()
            flash('Account created successfully! Please login.', 'success')
            return redirect(url_for('index'))
        except sqlite3.IntegrityError:
            flash('Email already exists', 'error')
        finally:
            conn.close()
            
    return render_template('auth.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully', 'success')
    return redirect(url_for('index'))

@app.route('/setup', methods=['GET', 'POST'])
def setup():
    if 'user_id' not in session:
        flash('Please login first', 'error')
        return redirect(url_for('index'))
        
    user_id = session['user_id']
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    if request.method == 'POST':
        driver_name = request.form.get('driver_name')
        car_number = request.form.get('car_number')
        blood_type = request.form.get('blood_type')
        telegram_id = request.form.get('telegram_id')
        
        cursor.execute('''
            UPDATE users 
            SET driver_name = ?, car_number = ?, blood_type = ?, telegram_id = ?
            WHERE id = ?
        ''', (driver_name, car_number, blood_type, telegram_id, user_id))
        conn.commit()
        
        session['driver_name'] = driver_name
        session['car_number'] = car_number
        session['blood_type'] = blood_type
        session['telegram_id'] = telegram_id
        flash('Profile updated! Please ensure your camera is positioned correctly.', 'success')
        conn.close()
        return redirect(url_for('face_verification'))
        
    cursor.execute("SELECT driver_name, car_number, blood_type, telegram_id FROM users WHERE id = ?", (user_id,))
    user = cursor.fetchone()
    conn.close()
    
    return render_template('setup.html', user=user)


@app.route('/face_verification')
def face_verification():
    if 'user_id' not in session:
        return redirect(url_for('index'))
    return render_template('camera_auth.html', mode='verify')

@app.route('/monitor')
def monitor():
    if 'user_id' not in session:
        return redirect(url_for('index'))
    return render_template('monitor.html')

# -------------------------------------------------------------------
# SESSION AND EVENT ROUTES

@app.route('/api/session/start', methods=['POST'])
def session_start():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401
        
    start_time = datetime.now().isoformat()
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT driver_name, car_number, blood_type, telegram_id FROM users WHERE id = ?", (user_id,))
    user = cursor.fetchone()
    if not user:
        conn.close()
        return jsonify({"error": "User not found"}), 404
        
    driver_name, car_number, blood_type, telegram_id = user
    
    cursor.execute('''
        INSERT INTO sessions (driver_name, car_number, blood_type, telegram_id, start_time)
        VALUES (?, ?, ?, ?, ?)
    ''', (driver_name, car_number, blood_type, telegram_id, start_time))
    
    session_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return jsonify({"session_id": session_id}), 200

import requests

def send_telegram_alert(chat_id, driver_name, car_number, event_type, lat, lng):
    if not chat_id or chat_id == "N/A":
        print(f"TELEGRAM ABORTED: Invalid chat_id = '{chat_id}'")
        return

    if event_type == 'emergency':
        header = "🆘 *EMERGENCY — DRIVER UNRESPONSIVE* 🆘"
        body = "Eyes closed for 3+ seconds. Driver may be unconscious!"
    else:
        header = "🚨 *WAKEDRIVE ALERT* 🚨"
        body = f"*{event_type.upper()} DETECTED!*"

    msg = f"{header}\n\nDriver: {driver_name}\nVehicle: {car_number}\nStatus: {body}\n"

    try:
        msg += f"\n📍 *Live Location:* [Open in Maps](https://maps.google.com/?q={float(lat)},{float(lng)})"
    except (TypeError, ValueError):
        msg += "\n📍 *Location:* GPS not available."
        
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    
    try:
        response = requests.post(url, json={"chat_id": chat_id, "text": msg, "parse_mode": "Markdown", "disable_web_page_preview": False}, timeout=10)
        if not response.ok:
            print(f"TELEGRAM API ERROR: {response.status_code} - {response.text}")
        else:
            print("Telegram alert sent successfully!")
    except Exception as e:
        print(f"Failed to send telegram alert: {e}")

@app.route('/api/event/log', methods=['POST'])
def log_event():
    data = request.json
    session_id = data.get('session_id')
    event_type = data.get('event_type')
    timestamp = data.get('timestamp', datetime.now().isoformat())
    lat = data.get('lat')
    lng = data.get('lng')
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('SELECT telegram_id FROM sessions WHERE id = ?', (session_id,))
    row = cursor.fetchone()
    db_telegram_id = row[0] if row else None
    print(f"DEBUG: log_event triggered - event_type: {event_type}, session_id: {session_id}, db_telegram_id: {db_telegram_id}")
    
    cursor.execute('''
        INSERT INTO events (session_id, event_type, timestamp)
        VALUES (?, ?, ?)
    ''', (session_id, event_type, timestamp))
    
    # If it's a severe event, fetch the user's telegram ID and send an alert
    if event_type in ['drowsy', 'emergency']:
        cursor.execute('SELECT driver_name, car_number, telegram_id FROM sessions WHERE id = ?', (session_id,))
        session_info = cursor.fetchone()
        if session_info:
            send_telegram_alert(session_info[2], session_info[0], session_info[1], event_type, lat, lng)
            
    conn.commit()
    conn.close()
    
    return jsonify({"success": True}), 200

@app.route('/api/session/end', methods=['POST'])
def session_end():
    data = request.json
    session_id = data.get('session_id')
    end_time = datetime.now()
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('SELECT start_time FROM sessions WHERE id = ?', (session_id,))
    row = cursor.fetchone()
    
    if not row:
        conn.close()
        return jsonify({"error": "Session not found"}), 404
        
    start_time = datetime.fromisoformat(row[0])
    duration_minutes = (end_time - start_time).total_seconds() / 60.0
    
    cursor.execute('''
        UPDATE sessions
        SET end_time = ?, duration_minutes = ?
        WHERE id = ?
    ''', (end_time.isoformat(), duration_minutes, session_id))
    
    cursor.execute('SELECT COUNT(*) FROM events WHERE session_id = ?', (session_id,))
    total_events = cursor.fetchone()[0]
    
    conn.commit()
    conn.close()
    
    return jsonify({"total_events": total_events, "duration_minutes": duration_minutes}), 200

@app.route('/api/session/history', methods=['GET'])
def session_history():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT s.id, s.driver_name, s.start_time, s.duration_minutes,
               COUNT(e.id) as event_count
        FROM sessions s
        LEFT JOIN events e ON s.id = e.session_id
        GROUP BY s.id
        ORDER BY s.start_time DESC
        LIMIT 10
    ''')
    
    sessions = []
    for row in cursor.fetchall():
        sessions.append({
            "id": row[0],
            "driver_name": row[1],
            "start_time": row[2],
            "duration_minutes": row[3],
            "event_count": row[4]
        })
        
    conn.close()
    return jsonify(sessions), 200


# FACE VERIFICATION ROUTES (MediaPipe)

def decode_base64_image(base64_string):
    if "," in base64_string:
        base64_string = base64_string.split(",")[1]
    img_data = base64.b64decode(base64_string)
    nparr = np.frombuffer(img_data, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    return img_rgb

@app.route('/api/face/verify', methods=['POST'])
def verify_face():
    data = request.json
    uid = data.get('uid')
    image_base64 = data.get('image_base64')
    
    if not all([uid, image_base64]):
        return jsonify({"verified": False, "error": "Missing parameters"}), 400
        
    try:
        img_rgb = decode_base64_image(image_base64)
        
        # Initialize MediaPipe Face Detection
        mp_face_detection = mp.solutions.face_detection
        with mp_face_detection.FaceDetection(model_selection=0, min_detection_confidence=0.5) as face_detection:
            results = face_detection.process(img_rgb)
            
            if results.detections:
                # A face was found!
                return jsonify({
                    "verified": True,
                    "confidence": float(results.detections[0].score[0])
                }), 200
            else:
                return jsonify({"verified": False, "error": "No face detected in submitted image"}), 400
                
    except Exception as e:
        print(f"Error verifying face: {e}")
        return jsonify({"verified": False, "error": str(e)}), 500


# -------------------------------------------------------------------
# DASHBOARD ROUTES
# -------------------------------------------------------------------

@app.route('/dashboard', methods=['GET'])
def dashboard():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 1. Total sessions and total drowsy events
    cursor.execute('SELECT COUNT(*) FROM sessions')
    total_sessions = cursor.fetchone()[0] or 0
    
    cursor.execute("SELECT COUNT(*) FROM events WHERE event_type = 'drowsy'")
    total_drowsy = cursor.fetchone()[0] or 0
    
    # 2. Most dangerous time of day (hour)
    cursor.execute('''
        SELECT strftime('%H', timestamp) as hour, COUNT(*) as count 
        FROM events 
        WHERE event_type IN ('drowsy', 'microsleep', 'emergency') 
        GROUP BY hour 
        ORDER BY count DESC 
        LIMIT 1
    ''')
    dangerous_hour_row = cursor.fetchone()
    dangerous_time = f"{dangerous_hour_row[0]}:00" if dangerous_hour_row else "N/A"
    
    # 3. Last 7 sessions vs drowsy events
    cursor.execute('''
        SELECT s.id, s.start_time, COUNT(e.id) as drowsy_count
        FROM sessions s
        LEFT JOIN events e ON s.id = e.session_id AND e.event_type = 'drowsy'
        GROUP BY s.id
        ORDER BY s.start_time DESC
        LIMIT 7
    ''')
    last_7_sessions = cursor.fetchall()
    # Reverse for chronological order in charts
    last_7_sessions.reverse()
    
    bar_chart_labels = [datetime.fromisoformat(r[1]).strftime("%b %d, %H:%M") for r in last_7_sessions]
    bar_chart_data = [r[2] for r in last_7_sessions]
    
    # 4. Line chart: microsleep events per session
    cursor.execute('''
        SELECT s.id, s.start_time, COUNT(e.id) as microsleep_count
        FROM sessions s
        LEFT JOIN events e ON s.id = e.session_id AND e.event_type = 'microsleep'
        GROUP BY s.id
        ORDER BY s.start_time DESC
        LIMIT 7
    ''')
    last_7_microsleeps = cursor.fetchall()
    last_7_microsleeps.reverse()
    
    line_chart_labels = [datetime.fromisoformat(r[1]).strftime("%b %d, %H:%M") for r in last_7_microsleeps]
    line_chart_data = [r[2] for r in last_7_microsleeps]
    
    # 5. Table of recent sessions
    cursor.execute('''
        SELECT s.driver_name, s.start_time, s.duration_minutes,
            SUM(CASE WHEN e.event_type = 'microsleep' THEN 1 ELSE 0 END) as micro_count,
            SUM(CASE WHEN e.event_type = 'drowsy' THEN 1 ELSE 0 END) as drowsy_count,
            SUM(CASE WHEN e.event_type = 'emergency' THEN 1 ELSE 0 END) as emergency_count
        FROM sessions s
        LEFT JOIN events e ON s.id = e.session_id
        GROUP BY s.id
        ORDER BY s.start_time DESC
        LIMIT 10
    ''')
    recent_sessions_raw = cursor.fetchall()
    
    recent_sessions = []
    for r in recent_sessions_raw:
        st = datetime.fromisoformat(r[1]).strftime("%Y-%m-%d %H:%M:%S")
        duration = round(r[2] or 0.0, 1)
        recent_sessions.append({
            "driver_name": r[0],
            "date": st,
            "duration": f"{duration} min",
            "microsleeps": r[3] or 0,
            "drowsy_events": r[4] or 0,
            "emergencies": r[5] or 0
        })
        
    conn.close()
    
    return render_template('dashboard.html',
                           total_sessions=total_sessions,
                           total_drowsy=total_drowsy,
                           dangerous_time=dangerous_time,
                           bar_chart_labels=bar_chart_labels,
                           bar_chart_data=bar_chart_data,
                           line_chart_labels=line_chart_labels,
                           line_chart_data=line_chart_data,
                           recent_sessions=recent_sessions)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
