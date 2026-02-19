#!/usr/bin/env python3
import subprocess, json, time, os, requests
SUPABASE_URL = "https://vbqbbziqleymxcyesmky.supabase.co"
SUPABASE_KEY = "sb_secret_lIbl-DBgnrt_fejgJjKqg_qR62SVEm"
DEVICE_ID = "zenith-phone"

def push():
    try:
        batt = json.loads(subprocess.check_output("termux-battery-status", shell=True))
        stats = {
            "device_id": DEVICE_ID,
            "battery": batt.get("percentage"),
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "status": "active"
        }
        requests.post(f"{SUPABASE_URL}/rest/v1/device_state", 
                      headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}, 
                      json=stats)
    except: pass

if __name__ == "__main__":
    while True:
        push()
        time.sleep(300)
