#!/usr/bin/env python3
import os, json, time, subprocess, requests, socket

URL = "https://vbqbbziqleymxcyesmky.supabase.co/rest/v1/device_state"
KEY = os.environ.get("SUPABASE_KEY", "")

def push_state():
    try:
        state = {
            "device_id": socket.gethostname(),
            "timestamp": time.time(),
            "uptime": subprocess.check_output("uptime", shell=True).decode().strip(),
            "battery": subprocess.check_output("termux-battery-status", shell=True).decode().strip()
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
    push_state()
