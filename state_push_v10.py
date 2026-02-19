
#!/usr/bin/env python3
import os, json, time, subprocess, logging
from urllib.request import Request, urlopen
from datetime import datetime, timezone

SUPABASE_URL = "https://vbqbbziqleymxcyesmky.supabase.co"
SUPABASE_KEY = "sb_secret_lIbl-DBgdnrt_fejgJjKqg_qR62SVEm" # Service role key
DEVICE_ID = "amos-arms"

def get_cmd(cmd):
    try:
        return subprocess.check_output(cmd, shell=True).decode().strip()
    except:
        return "unknown"

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
            "android_version": get_cmd("getprop ro.build.version.release"),
            "termux_version": get_cmd("termux-info | grep 'Termux app' | cut -d: -f2"),
            "hostname": get_cmd("hostname"),
            "network": get_cmd("termux-wifi-connectioninfo | grep ssid | cut -d: -f2") or "mobile",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "raw_output": f"Uptime: {get_cmd('uptime')}"
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
        print(f"Push error: {e}")
        return 500

if __name__ == "__main__":
    print("State Pusher v10.0 Starting...")
    while True:
        code = push_state()
        print(f"State push: {code}")
        time.sleep(300) # Every 5 min
