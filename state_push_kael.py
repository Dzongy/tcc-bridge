#!/usr/bin/env python3
import os, json, subprocess, time
from urllib.request import urlopen, Request

URL = "https://vbqbbziqleymxcyesmky.supabase.co/rest/v1/device_state"
KEY = "sb_secret_lIbl-DBgdnrt_fejgJjKqg_qR62SVEm"

def get_state():
    try:
        # Get battery
        batt = json.loads(subprocess.check_output("termux-battery-status", shell=True))
        # Get network
        net = subprocess.check_output("termux-telephony-deviceinfo", shell=True).decode()
        # Get storage
        storage = subprocess.check_output("df -h /data", shell=True).decode()
        
        return {
            "device_id": "amos-arms",
            "battery": batt.get("percentage"),
            "network": net,
            "storage": {"raw": storage},
            "hostname": subprocess.check_output("hostname", shell=True).decode().strip(),
            "termux_version": os.environ.get("TERMUX_VERSION", "unknown"),
            "raw_output": f"Battery: {batt.get('status')}, {batt.get('percentage')}%"
        }
    except Exception as e:
        return {"error": str(e)}

def push():
    data = get_state()
    headers = {
        "apikey": KEY,
        "Authorization": f"Bearer {KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal"
    }
    req = Request(URL, data=json.dumps(data).encode(), headers=headers, method="POST")
    try:
        with urlopen(req) as response:
            print(f"Pushed state: {response.status}")
    except Exception as e:
        print(f"Failed to push: {e}")

if __name__ == "__main__":
    push()
