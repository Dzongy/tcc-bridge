#!/usr/bin/env python3
"""
TCC Watchdog — Monitors Bridge and Tunnel.
"""

import os, subprocess, time, requests, json

TUNNEL_URL = "https://zenith.cosmic-claw.com/health"
NTFY_URL = "https://ntfy.sh/tcc-zenith-hive"

def check_health():
    try:
        r = requests.get(TUNNEL_URL, timeout=10)
        if r.status_code == 200:
            return True
    except:
        pass
    return False

def notify(msg):
    try:
        requests.post(NTFY_URL, data=msg.encode('utf-8'))
    except:
        pass

if __name__ == "__main__":
    while True:
        if not check_health():
            print("Bridge unreachable, checking processes...")
            # Check if bridge.py is running (via PM2 preferably, but here we just restart if needed)
            # Actually, PM2 handles the restart. This watchdog is to notify if even PM2 can't fix it.
            notify("⚠️ Bridge/Tunnel unreachable at zenith.cosmic-claw.com")
        
        time.sleep(300) # Check every 5 mins
