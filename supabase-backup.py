#!/usr/bin/env python3
import os, json, time, subprocess, requests, socket

URL = "https://vbqbbziqleymxcyesmky.supabase.co/rest/v1/device_state"
KEY = os.environ.get("SUPABASE_KEY", "sb_secret_lIbl-DBgdnrt_fejgJjKqg_qR62SVEm")

def push_state():
    try:
        # Get termux info
        battery = subprocess.check_output("termux-battery-status", shell=True).decode().strip()
        wifi = subprocess.check_output("termux-wifi-connectioninfo", shell=True).decode().strip()
        
        state = {
            "device_id": socket.gethostname(),
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "battery": json.loads(battery),
            "network": json.loads(wifi),
            "status": "online"
        }
        
        headers = {
            "apikey": KEY,
            "Authorization": f"Bearer {KEY}",
            "Content-Type": "application/json",
            "Prefer": "resolution=merge-duplicates"
        }
        res = requests.post(URL, json=state, headers=headers)
        print(f"Push result: {res.status_code}")
    except Exception as e:
        print(f"Push failed: {e}")

if __name__ == "__main__":
    while True:
        push_state()
        time.sleep(300) # 5 minutes
