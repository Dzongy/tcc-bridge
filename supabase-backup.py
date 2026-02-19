#!/usr/bin/env python3
import os, json, socket, subprocess, time
from urllib.request import Request, urlopen

SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://vbqbbziqleymxcyesmky.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")

def get_stats():
    try:
        battery_out = subprocess.check_output("termux-battery-status", shell=True).decode()
        battery = json.loads(battery_out)
        storage = subprocess.check_output("df -h /data", shell=True).decode()
        return {
            "hostname": socket.gethostname(),
            "battery": int(battery.get("percentage", 0)),
            "android_version": subprocess.check_output("getprop ro.build.version.release", shell=True).decode().strip(),
            "termux_version": os.environ.get("TERMUX_VERSION", "unknown"),
            "network": subprocess.check_output("termux-wifi-connectioninfo", shell=True).decode().strip(),
            "raw_output": storage
        }
    except Exception as e:
        print(f"Stats collection failed: {e}")
        return {}

def push():
    if not SUPABASE_KEY:
        print("Missing SUPABASE_KEY")
        return
    stats = get_stats()
    if not stats: return
    
    url = f"{SUPABASE_URL}/rest/v1/device_state"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates"
    }
    payload = {
        "device_id": stats["hostname"],
        "hostname": stats["hostname"],
        "battery": stats["battery"],
        "android_version": stats["android_version"],
        "termux_version": stats["termux_version"],
        "network": stats["network"],
        "raw_output": stats["raw_output"]
    }
    
    try:
        req = Request(url, data=json.dumps(payload).encode(), headers=headers, method="POST")
        urlopen(req)
        print("Stats pushed to Supabase")
    except Exception as e:
        print(f"Push failed: {e}")

if __name__ == '__main__':
    push()
