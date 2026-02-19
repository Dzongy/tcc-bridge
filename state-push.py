#!/usr/bin/env python3
import os, json, time, subprocess
from datetime import datetime, timezone
from urllib.request import urlopen, Request

SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://vbqbbziqleymxcyesmky.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")
DEVICE_ID    = "amos-arms"

def get_battery():
    try:
        res = subprocess.check_output("termux-battery-status", shell=True).decode()
        return json.loads(res)
    except: return {}

def push():
    if not SUPABASE_KEY: return
    payload = {
        "device_id": DEVICE_ID,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "battery": get_battery(),
        "status": "active"
    }
    try:
        url = f"{SUPABASE_URL}/rest/v1/device_state"
        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json",
            "Prefer": "resolution=merge-duplicates"
        }
        req = Request(url, data=json.dumps(payload).encode(), headers=headers, method="POST")
        urlopen(req, timeout=10)
    except Exception as e:
        print(f"Push failed: {e}")

if __name__ == "__main__":
    while True:
        push()
        time.sleep(300)
