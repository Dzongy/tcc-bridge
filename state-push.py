#!/usr/bin/env python3
import time, requests, os, json, subprocess

SUPABASE_URL = "https://vbqbbziqleymxcyesmky.supabase.co"
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "sb_secret_lIbl-DBgnrt_fejgJjKqg_qR62SVEm")
DEVICE_ID = "amos-arms"

def get_stats():
    stats = {
        "device_id": DEVICE_ID,
        "android_version": subprocess.getoutput("getprop ro.build.version.release"),
        "termux_version": "v0.118",
        "hostname": subprocess.getoutput("hostname"),
        "battery": 0,
        "network": "unknown",
        "storage": {},
        "apps_json": {},
        "raw_output": ""
    }
    
    try:
        batt = json.loads(subprocess.getoutput("termux-battery-status"))
        stats["battery"] = int(batt.get("percentage", 0))
    except: pass
    
    try:
        net = json.loads(subprocess.getoutput("termux-telephony-deviceinfo"))
        stats["network"] = net.get("network_type", "unknown")
    except: pass

    try:
        df = subprocess.getoutput("df -h /data")
        stats["storage"] = {"info": df}
    except: pass
    
    return stats

def push_state():
    stats = get_stats()
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal"
    }
    try:
        r = requests.post(f"{SUPABASE_URL}/rest/v1/device_state", headers=headers, json=stats)
        print(f"Push status: {r.status_code}")
    except Exception as e:
        print(f"Push failed: {e}")

if __name__ == '__main__':
    push_state()