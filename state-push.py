#!/usr/bin/env python3
"""TCC Bridge — State Push (PM2 managed)
Reports device state to Supabase + alerts via ntfy if services down.
"""
import subprocess, json, os, sys, time
from urllib.request import Request, urlopen

SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://vbqbbziqleymxcyesmky.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")
NTFY_TOPIC   = os.environ.get("NTFY_TOPIC",   "tcc-zenith-hive")

def push_to_supabase(data):
    if not SUPABASE_KEY: return
    try:
        req = Request(f"{SUPABASE_URL}/rest/v1/device_state", 
                      data=json.dumps(data).encode(),
                      headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}", "Content-Type": "application/json", "Prefer": "resolution=merge-duplicates"})
        urlopen(req, timeout=10)
    except Exception as e:
        print(f"Supabase push failed: {e}")

def notify_ntfy(msg, priority=3):
    try:
        urlopen(f"https://ntfy.sh/{NTFY_TOPIC}", data=msg.encode(), timeout=5)
    except: pass

def main():
    while True:
        state = {
            "device_id": "amos-arms",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "bridge_online": False,
            "tunnel_online": False
        }
        # Check local bridge
        try:
            urlopen("http://localhost:8080/health", timeout=5)
            state["bridge_online"] = True
        except: pass

        # Check tunnel
        try:
            urlopen("https://zenith.cosmic-claw.com/health", timeout=5)
            state["tunnel_online"] = True
        except: pass
        
        # Push to Supabase
        push_to_supabase(state)
        
        # Alert if down
        if not state["bridge_online"] or not state["tunnel_online"]:
            notify_ntfy(f"⚠️ BRIDGE ALERT: Bridge={state['bridge_online']}, Tunnel={state['tunnel_online']}", priority=4)
        
        time.sleep(300) # Wait 5 mins (PM2 might also handle the loop if autorestart=true and script exits)

if __name__ == "__main__":
    main()
