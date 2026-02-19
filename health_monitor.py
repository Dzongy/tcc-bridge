#!/usr/bin/env python3
import time
import urllib.request
import json
import os

NTFY_URL = "https://ntfy.sh/tcc-zenith-hive"
CHECK_URL = "https://zenith.cosmic-claw.com/health"

def notify(msg, priority=3):
    try:
        req = urllib.request.Request(NTFY_URL, data=msg.encode(), headers={"Title": "Bridge Health Alert", "Priority": str(priority)})
        urllib.request.urlopen(req)
    except:
        pass

while True:
    try:
        resp = urllib.request.urlopen(CHECK_URL, timeout=10)
        if resp.status != 200:
            notify("⚠️ Bridge Health Check Failed: Status " + str(resp.status), 4)
    except Exception as e:
        notify("🚨 BRIDGE DOWN: Cannot reach zenith.cosmic-claw.com. " + str(e), 5)
    
    time.sleep(300) # Check every 5 mins
