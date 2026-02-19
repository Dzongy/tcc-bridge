#!/usr/bin/env python3
"""
TCC Bridge — State Push v2.0
"""
import subprocess, json, os, sys, time
from urllib.request import Request, urlopen

SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://vbqbbziqleymxcyesmky.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")
NTFY_TOPIC   = os.environ.get("NTFY_TOPIC", "tcc-zenith-hive")
DEVICE_ID    = "amos-arms"

def get_output(cmd):
    try: return subprocess.check_output(cmd, shell=True).decode('utf-8').strip()
    except: return "N/A"

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
    except Exception as e: print(f"Supabase push failed: {e}")

def main():
    while True:
        try:
            battery = get_output("termux-battery-status")
            battery_pct = json.loads(battery).get("percentage", 0) if battery != "N/A" else 0
            
            state = {
                "device_id": DEVICE_ID,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "android_version": get_output("getprop ro.build.version.release"),
                "termux_version": get_output("termux-info | grep 'Termux' | head -n 1"),
                "hostname": socket.gethostname() if 'socket' in globals() else "amos-phone",
                "battery": battery_pct,
                "network": get_output("termux-wifi-connectioninfo"),
                "raw_output": f"Bridge Health: {get_output('curl -s http://localhost:8080/health')}"
            }
            push_to_supabase(state)
        except Exception as e: print(f"Push loop error: {e}")
        time.sleep(300) # Every 5 mins

if __name__ == "__main__":
    import socket
    main()
