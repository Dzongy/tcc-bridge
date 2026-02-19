#!/usr/bin/env python3
"""
state_push.py v3.0.0 — TCC Master Monitor
God Builder: Kael

Reports device health to Supabase and monitors Tunnel connectivity.
Alerts ntfy.sh/tcc-zenith-hive on failure.
"""

import json
import os
import subprocess
import time
from datetime import datetime
from urllib.request import Request, urlopen
from urllib.error import URLError

# --- CONFIG ---
SUPABASE_URL = "https://vbqbbziqleymxcyesmky.supabase.co"
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "sb_secret_lIbl-DBgnrt_fejgJjKqg_qR62SVEm")
NTFY_TOPIC   = os.environ.get("NTFY_TOPIC", "tcc-zenith-hive")
TUNNEL_URL   = "https://zenith.cosmic-claw.com/health"
DEVICE_ID    = "amos-arms"
INTERVAL     = 300 # 5 minutes

def get_stats():
    stats = {
        "device_id": DEVICE_ID,
        "hostname": subprocess.getoutput("hostname"),
        "battery": int(subprocess.getoutput("termux-battery-status | jq .percentage")),
        "network": subprocess.getoutput("termux-wifi-connectioninfo | jq -r .ssid"),
        "android_version": subprocess.getoutput("getprop ro.build.version.release"),
        "termux_version": os.environ.get("TERMUX_VERSION", "unknown"),
        "storage": json.loads(subprocess.getoutput("df -h /data --output=pcent,avail | tail -n 1 | awk '{print \"{\\\"pcent\\\":\\\"\" $1 \"\\\",\\\"avail\\\":\\\"\" $2 \"\\\"}\"}'")),
        "timestamp": datetime.now().isoformat()
    }
    return stats

def push_to_supabase(data):
    try:
        req = Request(f"{SUPABASE_URL}/rest/v1/device_state", 
                    data=json.dumps(data).encode(),
                    headers={
                        "apikey": SUPABASE_KEY,
                        "Authorization": f"Bearer {SUPABASE_KEY}",
                        "Content-Type": "application/json",
                        "Prefer": "resolution=merge-duplicates"
                    })
        urlopen(req, timeout=15)
        return True
    except Exception as e:
        print(f"Supabase push failed: {e}")
        return False

def check_tunnel():
    try:
        with urlopen(TUNNEL_URL, timeout=10) as response:
            return response.getcode() == 200
    except:
        return False

def ntfy_alert(msg, priority=4):
    try:
        req = Request(f"https://ntfy.sh/{NTFY_TOPIC}", data=msg.encode())
        req.add_header("Priority", str(priority))
        req.add_header("Title", "BRIDGE ALERT")
        req.add_header("Tags", "warning,robot")
        urlopen(req, timeout=5)
    except:
        pass

def main():
    print("Master Monitor V3 starting...")
    while True:
        stats = get_stats()
        push_to_supabase(stats)
        
        if not check_tunnel():
            print("Tunnel health check FAILED!")
            ntfy_alert(f"⚠️ BRIDGE DOWN: Tunnel at {TUNNEL_URL} is unreachable.")
        else:
            print("Tunnel health check OK.")
            
        time.sleep(INTERVAL)

if __name__ == "__main__":
    main()
