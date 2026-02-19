#!/usr/bin/env python3
import os, time, json, socket, subprocess
from urllib.request import Request, urlopen

SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://vbqbbziqleymxcyesmky.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")
DEVICE_ID = "kael-phone-01"

def push_state():
    if not SUPABASE_KEY:
        print("No Supabase key, skipping push")
        return

    try:
        # Collect state
        uptime_res = subprocess.run(["uptime", "-p"], capture_output=True, text=True)
        battery_res = subprocess.run(["termux-battery-status"], capture_output=True, text=True)
        
        state = {
            "device_id": DEVICE_ID,
            "timestamp": time.time(),
            "uptime": uptime_res.stdout.strip(),
            "battery": json.loads(battery_res.stdout) if battery_res.returncode == 0 else {},
            "status": "online"
        }

        # Push to Supabase zenith_messages or a custom state table
        # Using a generic RPC or table insert
        url = f"{SUPABASE_URL}/rest/v1/kael_memory"
        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json",
            "Prefer": "return=minimal"
        }
        
        # Wrapping state in memory structure
        payload = {
            "key": "device_state",
            "value": state,
            "updated_at": "now()"
        }
        
        req = Request(url, data=json.dumps(payload).encode(), headers=headers, method="POST")
        with urlopen(req) as f:
            pass
        print("State pushed to Supabase")
        
    except Exception as e:
        print(f"Push failed: {e}")

if __name__ == "__main__":
    while True:
        push_state()
        time.sleep(300) # Every 5 mins
