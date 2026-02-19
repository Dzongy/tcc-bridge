#!/usr/bin/env python3
import time, urllib.request, json

HEALTH_URL = "https://zenith.cosmic-claw.com/health"
NTFY_URL = "https://ntfy.sh/tcc-zenith-hive"

def alert(msg):
    try:
        req = urllib.request.Request(NTFY_URL, data=msg.encode(), headers={
            "Title": "BRIDGE DOWN", 
            "Priority": "5", 
            "Tags": "warning,robot"
        })
        urllib.request.urlopen(req)
    except: pass

while True:
    try:
        with urllib.request.urlopen(HEALTH_URL, timeout=10) as r:
            if r.getcode() != 200:
                alert("Bridge returned non-200 status")
    except Exception as e:
        alert(f"Bridge inaccessible: {e}")
    time.sleep(300)
