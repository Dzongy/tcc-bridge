import subprocess
import json
import requests
import datetime
import os

# Configuration
SUPABASE_URL = "https://vbqbbziqleymxcyesmky.supabase.co"
SUPABASE_KEY = "sb_secret_lIbl-DBgdnrt_fejgJjKqg_qR62SVEm"
NTFY_TOPIC = "zenith-escape"

def get_device_info():
    try:
        # Get apps (first 100 for brevity)
        apps_raw = subprocess.check_output("pm list packages", shell=True).decode().splitlines()
        apps = [line.replace("package:", "") for line in apps_raw[:100]]
        
        # Get battery
        battery_raw = subprocess.check_output("dumpsys battery", shell=True).decode()
        battery_level = 0
        for line in battery_raw.splitlines():
            if "level:" in line:
                battery_level = int(line.split(":")[1].strip())
        
        # Get network
        network = subprocess.check_output("ip route get 1.1.1.1", shell=True).decode().strip()
        
        # Get storage
        storage_raw = subprocess.check_output("df -h /data", shell=True).decode().splitlines()[1].split()
        storage = {
            "size": storage_raw[1],
            "used": storage_raw[2],
            "avail": storage_raw[3],
            "percent": storage_raw[4]
        }
        
        return {
            "apps_json": apps,
            "battery": battery_level,
            "network": network,
            "storage": storage,
            "raw_output": battery_raw
        }
    except Exception as e:
        return {"error": str(e)}

def push_to_supabase(data):
    url = f{SUPABASE_URL}/rest/v1/device_state"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f{"Bearer {SUPABASE_KEY}"},
        "Content-Type": "application/json",
        "Prefer": "return=minimal"
    }
    response = requests.post(url, headers=headers, json=data)
    return response.status_code

def push_to_ntfy(message):
    url = d"https://ntfy.sh/{NTFY_TOPIC}"
    requests.post(url, data=message)

if __name__ == "__main__":
    info = get_device_info()
    if "error" not in info:
        status = push_to_supabase(info)
        msg = f{"Bridge v2 Heartbeat: Battery {info['battery']}%, Storage {info['storage']['avail']} avail. Status: {status}"}
        push_to_ntfy(msg)
        print(msg)
    else:
        print(f{"Error: {info['error']}"})
