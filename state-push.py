#!/usr/bin/env python3
"""
TCC Bridge — State Push v2.0
Reports device state to Supabase + health check.
"""
import subprocess, json, os, sys, time, socket
from urllib.request import Request, urlopen

SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://vbqbbziqleymxcyesmky.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")
DEVICE_ID    = os.environ.get("DEVICE_ID", "amos-arms")
NTFY_TOPIC   = os.environ.get("NTFY_TOPIC", "tcc-zenith-hive")

def get_output(cmd):
    try: return subprocess.check_output(cmd, shell=True, text=True).strip()
    except: return ""

def push_state(data):
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
    except Exception as e: print(f"Push failed: {e}")

def check_bridge():
    try:
        with socket.create_connection(("localhost", 8080), timeout=2): return True
    except: return False

def main():
    while True:
        try:
            battery = get_output("termux-battery-status")
            bat_json = json.loads(battery) if battery else {}
            
            state = {
                "device_id": DEVICE_ID,
                "hostname": socket.gethostname(),
                "android_version": get_output("getprop ro.build.version.release"),
                "termux_version": get_output("termux-info | grep 'Termux version' | cut -d: -f2"),
                "battery": bat_json.get("percentage", 0),
                "network": get_output("termux-telephony-deviceinfo | grep 'network_type' | cut -d: -f2"),
                "raw_output": f"Bridge Online: {check_bridge()}"
            }
            push_state(state)
        except Exception as e:
            print(f"Error in state push loop: {e}")
        
        time.sleep(300) # Every 5 mins

if __name__ == "__main__":
    main()
