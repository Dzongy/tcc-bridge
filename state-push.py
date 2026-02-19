#!/usr/bin/env python3
"""
state-push.py v2.0.0 — TCC Bridge Health & State Reporter
God Builder: Kael
"""

import json
import os
import subprocess
import time
from datetime import datetime
from urllib.request import Request, urlopen

# --- Config ---
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://vbqbbziqleymxcyesmky.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")
NTFY_TOPIC   = os.environ.get("NTFY_TOPIC", "tcc-zenith-hive")
DEVICE_ID    = "amos-arms"

def push_to_supabase(data):
    if not SUPABASE_KEY: return
    try:
        req = Request(f"{SUPABASE_URL}/rest/v1/device_state", 
                      data=json.dumps(data).encode(),
                      headers={
                          "apikey": SUPABASE_KEY,
                          "Authorization": f"Bearer {SUPABASE_KEY}",
                          "Content-Type": "application/json",
                          "Prefer": "resolution=merge-duplicates"
                      })
        urlopen(req, timeout=10)
    except Exception as e:
        print(f"Supabase push failed: {e}")

def ntfy_alert(msg, priority=4):
    try:
        req = Request(f"https://ntfy.sh/{NTFY_TOPIC}", data=msg.encode())
        req.add_header("Priority", str(priority))
        req.add_header("Title", "Bridge Health Alert")
        urlopen(req, timeout=5)
    except: pass

def check_health(url):
    try:
        with urlopen(url, timeout=5) as r:
            return r.status == 200
    except: return False

def main():
    last_tunnel_status = True
    while True:
        try:
            # Check local bridge
            bridge_up = check_health("http://localhost:8080/health")
            
            # Check external tunnel
            tunnel_up = check_health("https://zenith.cosmic-claw.com/health")
            
            state = {
                "device_id": DEVICE_ID,
                "timestamp": datetime.now().isoformat(),
                "bridge_online": bridge_up,
                "tunnel_online": tunnel_up,
                "version": "7.0.0"
            }
            
            push_to_supabase(state)
            
            # Alert on tunnel drop
            if bridge_up and not tunnel_up and last_tunnel_status:
                ntfy_alert("⚠️ Tunnel is DOWN but Bridge is UP! Zenith unreachable.", priority=5)
            
            last_tunnel_status = tunnel_up
            
        except Exception as e:
            print(f"Loop error: {e}")
            
        time.sleep(300) # Every 5 minutes

if __name__ == "__main__":
    main()
