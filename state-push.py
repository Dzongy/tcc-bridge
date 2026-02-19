#!/usr/bin/env python3
import os, json, time, subprocess, logging
from urllib.request import Request, urlopen
from datetime import datetime, timezone

SUPABASE_URL = "https://vbqbbziqleymxcyesmky.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZicWJiemlxbGV5bXhjeWVzbWt5Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3MTExMTUxNiwiZXhwIjoyMDg2Njg3NTE2fQ.MREdeLv0R__fHe61lOYSconedoo_qHItZUpmcR-IORQ"
DEVICE_ID = "amos-arms"

def get_battery():
    try:
        res = subprocess.check_output("termux-battery-status", shell=True).decode()
        return json.loads(res).get("percentage", 0)
    except:
        return 0

def push_state():
    try:
        data = {
            "device_id": DEVICE_ID,
            "battery": get_battery(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "online"
        }
        
        req = Request(f"{SUPABASE_URL}/rest/v1/device_state", 
                      data=json.dumps(data).encode(),
                      headers={
                          "apikey": SUPABASE_KEY,
                          "Authorization": f"Bearer {SUPABASE_KEY}",
                          "Content-Type": "application/json",
                          "Prefer": "return=minimal"
                      }, method="POST")
        
        with urlopen(req) as res:
            print(f"State pushed: {res.status}")
    except Exception as e:
        print(f"Push failed: {e}")

if __name__ == "__main__":
    push_state()
