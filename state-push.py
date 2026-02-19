#!/usr/bin/env python3
import os, json, time, subprocess, logging
from urllib.request import Request, urlopen
from datetime import datetime, timezone

SUPABASE_URL = "https://vbqbbziqleymxcyesmky.supabase.co"
SUPABASE_KEY = "sb_secret_lIbl-DBgdnrt_fejgJjKqg_qR62SVEm"
DEVICE_ID = "amos-arms"

def get_battery():
    try:
        res = subprocess.check_output("termux-battery-status", shell=True).decode()
        return json.loads(res).get("percentage", 0)
    except:
        return 0

def push_state():
    try:
        data = {
            "device_id": DEVICE_ID,
            "battery": get_battery(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "online"
        }
        
        req = Request(f"{SUPABASE_URL}/rest/v1/device_state", 
                      data=json.dumps(data).encode(),
                      headers={
                          "apikey": SUPABASE_KEY,
                          "Authorization": f"Bearer {SUPABASE_KEY}",
                          "Content-Type": "application/json",
                          "Prefer": "resolution=merge-duplicates"
                      })
        with urlopen(req) as response:
            return response.getcode()
    except Exception as e:
        print(f"Push failed: {e}")
        return None

if __name__ == "__main__":
    push_state()
