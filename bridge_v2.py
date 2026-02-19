
import subprocess
import json
import requests
import datetime
import os

# Config
SUPABASE_URL = "https://vbqbbziqleymxcyesmky.supabase.co"
SUPABASE_KEY = "sb_secret_lIbl-DBgdnrt_fejgJjKqg_qR62SVEm"
NTFY_TOPIC = "zenith-escape"

def get_output(cmd):
    try:
        return subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT).decode().strip()
    except:
        return ""

def main():
    print(f"[{datetime.datetime.now()}] Starting Bridge v2.0 update...")
    
    # Collect data
    apps = get_output("pm list packages | head -n 100")
    battery = get_output("termux-battery-status")
    network = get_output("termux-telephony-deviceinfo")
    storage = get_output("df -h /data")
    
    data = {
        "apps_json": {"packages": apps.split("\n")},
        "battery": battery,
        "network": network,
        "storage": storage,
        "raw_output": f"Update at {datetime.datetime.now()}"
    }
    
    # Push to Supabase
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal"
    }
    
    try:
        r = requests.post(f"{SUPABASE_URL}/rest/v1/device_state", headers=headers, json=data)
        print(f"Supabase status: {r.status_code}")
    except Exception as e:
        print(f"Supabase error: {e}")
        
    # Push to ntfy
    try:
        requests.post(f"https://ntfy.sh/{NTFY_TOPIC}", data=f"Bridge v2.0 Heartbeat: Battery {json.loads(battery).get('percentage', '?')}% | Apps cataloged.")
    except:
        pass

if __name__ == "__main__":
    main()
