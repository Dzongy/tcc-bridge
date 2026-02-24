
import requests
import json
import time
import subprocess
import os

# CREDENTIALS
SUPABASE_URL = "https://vbqbbziqleymxcyesmky.supabase.co"
SUPABASE_KEY = "sb_secret_lIbl-DBgdnrt_fejgJjKqg_qR62SVEm"
NTFY_TOPIC = "zenith-escape"

def get_device_state():
    try:
        # Get battery
        battery = subprocess.check_output(["termux-battery-status"]).decode("utf-8")
        # Get network
        network = subprocess.check_output(["termux-telephony-deviceinfo"]).decode("utf-8")
        # Get storage
        storage = subprocess.check_output(["df", "-h", "/data"]).decode("utf-8")
        # Get apps (first 100)
        apps = subprocess.check_output(["pm", "list", "packages"]).decode("utf-8").split("\n")[:100]
        
        return {
            "battery": json.loads(battery),
            "network": json.loads(network),
            "storage": storage,
            "apps": apps,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }
    except Exception as e:
        return {"error": str(e)}

def push_to_supabase(state):
    url = f"{SUPABASE_URL}/rest/v1/device_state"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal"
    }
    payload = {
        "apps_json": state.get("apps"),
        "battery": state.get("battery"),
        "network": state.get("network"),
        "storage": {"raw": state.get("storage")},
        "device_id": "commander-phone"
    }
    try:
        r = requests.post(url, headers=headers, json=payload)
        return r.status_code
    except:
        return 500

def notify_ntfy(message):
    requests.post(f"https://ntfy.sh/{NTFY_TOPIC}", data=message)

if __name__ == "__main__":
    state = get_device_state()
    status = push_to_supabase(state)
    if status == 201:
        notify_ntfy("✅ Bridge V2: Heartbeat pushed to Supabase.")
    else:
        notify_ntfy(f"❌ Bridge V2: Failed to push state (Status: {status})")
