#!/usr/bin/env python3
"""
TCC Bridge — State Push v3.0.0
Pushes device telemetry to Supabase and ntfy.
"""
import subprocess, json, os, socket, time
from urllib.request import Request, urlopen

SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://vbqbbziqleymxcyesmky.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")
NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "tcc-zenith-hive")
DEVICE_ID = socket.gethostname()

def get_output(cmd):
    try: return subprocess.check_output(cmd, shell=True).decode().strip()
    except: return "N/A"

def push():
    battery = json.loads(get_output("termux-battery-status"))
    wifi = json.loads(get_output("termux-wifi-connectioninfo"))
    
    data = {
        "device_id": DEVICE_ID,
        "battery_pct": battery.get("percentage"),
        "battery_status": battery.get("status"),
        "wifi_sssid": wifi.get("ssid"),
        "uptime": get_output("uptime -p"),
        "last_checkin": time.strftime('%Y-%m-%d %H:%M:%S')
    }
    
    if SUPABASE_KEY:
        req = Request(f"{SUPABASE_URL}/rest/v1/device_state", 
            data=json.dumps(data).encode(),
            headers={
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}",
                "Content-Type": "application/json",
                "Prefer": "resolution=merge-duplicates"
            })
        try: urlopen(req, timeout=10)
        except Exception as e: print(f"Supabase error: {e}")

if __name__ == "__main__":
    while True:
        push()
        time.sleep(300)
