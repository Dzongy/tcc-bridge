#!/usr/bin/env python3
import time, requests, os, json, subprocess

SUPABASE_URL = "https://vbqbbziqleymxcyesmky.supabase.co"
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "sb_secret_lIbl-DBgnrt_fejgJjKqg_qR62SVEm")
DEVICE_ID = "HERO_PHONE"

def get_stats():
    stats = {
        "device_id": DEVICE_ID,
        "battery": 0,
        "android_version": subprocess.getoutput("getprop ro.build.version.release"),
        "termux_version": subprocess.getoutput("termux-info | grep 'Packages' -A 1 | tail -n 1"),
        "hostname": subprocess.getoutput("hostname"),
        "network": "unknown",
        "raw_output": ""
    }
    
    # Battery
    try:
        batt = json.loads(subprocess.getoutput("termux-battery-status"))
        stats["battery"] = batt.get("percentage", 0)
    except: pass
    
    # Network
    try:
        net = json.loads(subprocess.getoutput("termux-telephony-deviceinfo"))
        stats["network"] = net.get("network_type", "unknown")
    except: pass
    
    return stats

def push_state():
    stats = get_stats()
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json"
    }
    try:
        r = requests.post(f"{SUPABASE_URL}/rest/v1/device_state", headers=headers, json=stats)
        print(f"State pushed: {r.status_code}")
    except Exception as e:
        print(f"Failed to push state: {e}")

if __name__ == "__main__":
    while True:
        push_state()
        time.sleep(300) # Every 5 minutes
