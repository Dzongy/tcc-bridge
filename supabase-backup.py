#!/usr/bin/env python3
import os, json, socket, subprocess, time
from urllib.request import Request, urlopen

SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://vbqbbziqleymxcyesmky.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")

def get_device_stats():
    return {
        "timestamp": int(time.time()),
        "hostname": socket.gethostname(),
        "uptime": subprocess.getoutput("uptime"),
        "battery": subprocess.getoutput("termux-battery-status"),
        "bridge_alive": "online" in subprocess.getoutput("curl -s http://localhost:8080/health")
    }

def push_to_supabase(data):
    if not SUPABASE_KEY: return
    url = f"{SUPABASE_URL}/rest/v1/device_state"
    headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}", "Content-Type": "application/json", "Prefer": "resolution=merge-duplicates"}
    payload = {"device_id": data["hostname"], "last_seen": data["timestamp"], "status": "online" if data["bridge_alive"] else "degraded", "raw_data": data}
    try:
        req = Request(url, data=json.dumps(payload).encode(), headers=headers, method="POST")
        with urlopen(req) as r: pass
    except Exception as e: print(f"Push failed: {e}")

if __name__ == "__main__":
    push_to_supabase(get_device_stats())