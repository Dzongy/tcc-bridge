#!/usr/bin/env python3
"""
TCC State Push — Pushes device state to Supabase.
"""

import os, json, time, subprocess, logging
from datetime import datetime, timezone
import urllib.request

SUPABASE_URL = "https://vbqbbziqleymxcyesmky.supabase.co"
SUPABASE_KEY = "sb_secret_lIbl-DBgdnrt_fejgJjKqg_qR62SVEm"

def get_device_info():
    try:
        battery = subprocess.check_output("termux-battery-status", shell=True).decode('utf-8')
        network = subprocess.check_output("termux-telephony-deviceinfo", shell=True).decode('utf-8')
        storage = subprocess.check_output("df -h /data/data/com.termux/files/home", shell=True).decode('utf-8')
        hostname = subprocess.check_output("hostname", shell=True).decode('utf-8').strip()
        
        return {
            "device_id": "amos-arms",
            "hostname": hostname,
            "battery": json.loads(battery).get('percentage', 0),
            "network": network,
            "storage": {"raw": storage},
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        return {"error": str(e)}

def push_to_supabase(data):
    url = f"{SUPABASE_URL}/rest/v1/device_state"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal"
    }
    req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8'), headers=headers, method='POST')
    try:
        with urllib.request.urlopen(req) as response:
            return response.status
    except Exception as e:
        print(f"Push failed: {e}")
        return None

if __name__ == "__main__":
    info = get_device_info()
    if "error" not in info:
        push_to_supabase(info)
