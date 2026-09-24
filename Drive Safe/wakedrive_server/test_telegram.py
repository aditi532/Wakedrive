import requests
import os
from dotenv import load_dotenv
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

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
        print(f"Sending message: {msg}")
        response = requests.post(url, json={"chat_id": chat_id, "text": msg, "parse_mode": "Markdown", "disable_web_page_preview": False}, timeout=10)
        print(response.status_code, response.text)
        if not response.ok:
            print(f"TELEGRAM API ERROR: {response.status_code} - {response.text}")
        else:
            print("Telegram alert sent successfully!")
    except Exception as e:
        print(f"Failed to send telegram alert: {e}")

send_telegram_alert('6316009723', 'aditi', 'DL123', 'drowsy', None, None)
