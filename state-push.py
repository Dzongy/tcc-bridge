#!/usr/bin/env python3
import subprocess, json, os, time
from urllib.request import Request, urlopen

SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://vbqbbziqleymxcyesmky.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")
NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "tcc-zenith-hive")

def push():
    try:
        # Get stats
        bat = subprocess.run("termux-battery-status", shell=True, capture_output=True, text=True).stdout
        stats = {"device_id": "amos-arms", "battery": json.loads(bat), "timestamp": time.time()}
        
        # Push to Supabase
        req = Request(f"{SUPABASE_URL}/rest/v1/device_state", 
                      data=json.dumps(stats).encode(),
                      headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}", "Content-Type": "application/json", "Prefer": "resolution=merge-duplicates"})
        urlopen(req, timeout=10)
    except Exception as e:
        print(f"Push failed: {e}")

if __name__ == "__main__":
    while True:
        push()
        time.sleep(300)
