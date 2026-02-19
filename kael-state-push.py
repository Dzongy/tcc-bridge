#!/usr/bin/env python3
import os, json, subprocess, socket, requests
from datetime import datetime

# CONFIG
URL = "https://vbqbbziqleymxcyesmky.supabase.co/rest/v1/device_state"
KEY = "sb_secret_lIbl-DBgdnrt_fejgJjKqg_qR62SVEm"
HEADERS = {
    "apikey": KEY,
    "Authorization": f"Bearer {KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=minimal"
}

def get_stats():
    try:
        battery = json.loads(subprocess.check_output(["termux-battery-status"]).decode())
        return {
            "device_id": socket.gethostname(),
            "battery": battery.get("percentage"),
            "hostname": socket.gethostname(),
            "timestamp": datetime.now().isoformat()
        }
    except: return None

stats = get_stats()
if stats:
    requests.post(URL, headers=HEADERS, json=stats)
