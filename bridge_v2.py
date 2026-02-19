import subprocess
import json
import requests
import time
from datetime import datetime

# CONFIG
SUPABASE_URL = "https://vbqbbziqleymxcyesmky.supabase.co/rest/v1/device_state"
SUPABASE_KEY = "sb_secret_lIbl-DBgdnrt_fejgJjKqg_qR62SVEm"
NTFY_URL = "https://ntfy.sh/zenith-escape"

def run_cmd(cmd):
    try:
        return subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT).decode('utf-8').strip()
    except Exception as e:
        return f"Error: {str(e)}"

def collect_state():
    print(f"[{datetime.now()}] Collecting state...")
    
    # Battery
    battery_raw = run_cmd("termux-battery-status")
    battery = 0
    try:
        battery = json.loads(battery_raw).get('percentage', 0)
    except:
        pass
        
    # Apps (first 100 for brevity)
    apps_raw = run_cmd("pm list packages")
    apps = [a.split(":")[1] for a in apps_raw.split("
") if ":" in a][:100]
    
    # Network
    network = run_cmd("termux-telephony-deviceinfo")
    
    # Storage
    storage = run_cmd("df -h /sdcard | tail -n 1")
    
    # Raw
    raw = f"Battery: {battery_raw}\nStorage: {storage}\nNetwork: {network}"
    
    data = {
        "apps_json": apps,
        "battery": battery,
        "network": network,
        "storage": storage,
        "raw_output": raw
    }
    
    return data

def push_to_supabase(data):
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal"
    }
    try:
        r = requests.post(SUPABASE_URL, json=data, headers=headers)
        print(f"Supabase response: {r.status_code}")
    except Exception as e:
        print(f"Supabase error: {e}")

def push_to_ntfy(data):
    msg = f"ZENITH BRIDGE HEARTBEAT\nBattery: {data['battery']}%\nApps: {len(data['apps_json'])}\nNetwork: {data['network'][:100]}..."
    try:
        requests.post(NTFY_URL, data=msg.encode('utf-8'))
    except:
        pass

if __name__ == '__main__':
    state = collect_state()
    push_to_supabase(state)
    push_to_ntfy(state)
