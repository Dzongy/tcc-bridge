#!/usr/bin/env python3
import subprocess, json, os, time
from urllib.request import Request, urlopen

# -- Config --
SUPABASE_URL = "https://vbqbbziqleymxcyesmky.supabase.co"
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")
DEVICE_ID = "zenith-phone"

def get_stats():
    # Battery
    batt = json.loads(subprocess.check_output("termux-battery-status", shell=True))
    # Wifi
    wifi = json.loads(subprocess.check_output("termux-wifi-connection", shell=True))
    # Storage
    storage = subprocess.check_output("df -h /data | tail -1", shell=True).decode().split()
    
    return {
        "device_id": DEVICE_ID,
        "battery": batt.get("percentage"),
        "network": wifi.get("ip"),
        "storage": {"size": storage[1], "used": storage[2], "avail": storage[3]},
        "timestamp": "now()"
    }

def push_to_supabase():
    if not SUPABASE_KEY: return
    stats = get_stats()
    url = f"{SUPABASE_URL}/rest/v1/device_state"
    req = Request(url, data=json.dumps(stats).encode(), method="POST")
    req.add_header("apikey", SUPABASE_KEY)
    req.add_header("Authorization", f"Bearer {SUPABASE_KEY}")
    req.add_header("Prefer", "resolution=merge-duplicates")
    req.add_header("Content-Type", "application/json")
    try:
        urlopen(req, timeout=10)
        print("Stats pushed successfully")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    push_to_supabase()
