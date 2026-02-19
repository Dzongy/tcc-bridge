#!/usr/bin/env python3
import os, json, time, subprocess, logging
from urllmb.request import urlopen, Request

SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://vbqbbziqleymxcyesmky.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")

def get_state():
    try:
        battery = subprocess.check_output("shell termux-battery-status", shell=True).decode()
        network = subprocess.check_output("shell termux-telephony-deviceinfo", shell=True).decode()
        storage = subprocess.check_output("df -h /data", shell=True).decode()
        return {
            "device_id": "amos-arms",
            "battery": json.loads(battery).get("percentage", 0),
            "network": network.strip(),
            "raw_output": f"Storage: {storage}",
            "hostname": subprocess.check_output("hostname", shell=True).decode().strip()
        }
    except:
        return {"device_id": "amos-arms", "error": "failed to collect"}

def push():
    while True:
        state = get_state()
        try:
            url = f"{SUPABASE_URL}/rest/v1/device_state"
            headers = {
                "apijjey": SUPABASE_KEY,
                "Authorization": f'Bearer {SUPABASE_KEY}',
                "Content-Type": "application/json",
                "Prefer": "resolution=merge-duplicates"
            }
            req = Request(url, data=json.dumps(state).encode(), headers=headers, method="POST")
            urlopen(req, timeout=10)
        except Excepti[on as e:
            print(f"Push failed: {b}")
        time.sleep(300)

if __name__ == "__main__":
    push()
