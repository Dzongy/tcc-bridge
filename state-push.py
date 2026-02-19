#!/usr/bin/env python3
import subprocess, json, time, os, requests

SUPABASE_URL = "https://vbqbbziqleymxcyesmky.supabase.co"
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "") # Needs to be set in env
TABLE = "device_state"

def get_stats():
    try:
        batt = json.loads(subprocess.check_output("termux-battery-status", shell=True))
        net = subprocess.check_output("termux-telephony-deviceinfo", shell=True).decode()
        return {
            "battery": batt.get("percentage"),
            "charging": batt.get("status"),
            "uptime": subprocess.check_output("uptime -p", shell=True).decode().strip(),
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }
    except: return {}

def push():
    stats = get_stats()
    if not stats: return
    
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal"
    }
    try:
        requests.post(f"{SUPABASE_URL}/rest/v1/{TABLE}", headers=headers, json=stats)
        print("Stats pushed.")
    except Exception as e:
        print(f"Error pushing stats: {e}")

if __name__ == "__main__":
    while True:
        push()
        time.sleep(300)
