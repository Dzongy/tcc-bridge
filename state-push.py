#!/usr/bin/env python3
"""TCC Bridge â State Push V2
Reports device health to Supabase every 5 mins.
"""
import subprocess, json, os, sys, time
from urllib.request import Request, urlopen

SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://vbqbbziqleymxcyesmky.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")
NTFY_TOPIC   = os.environ.get("NTFY_TOPIC", "tcc-zenith-hive")

def get_stats():
    try:
        batt = json.loads(subprocess.check_output(["termux-battery-status"]).decode())
        uptime = subprocess.check_output(["uptime", "-p"]).decode().strip()
        return {"battery": batt.get("percentage"), "plugged": batt.get("status"), "uptime": uptime}
    except:
        return {"battery": 0, "plugged": "unknown", "uptime": "unknown"}

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
        stats = get_stats()
        payload = {
            "device_id": "amos-arms",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "battery_level": stats["battery"],
            "status": "online",
            "metadata": stats
        }
        push_to_supabase(payload)
        time.sleep(300)

if __name__ == "__main__":
    main()
