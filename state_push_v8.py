#!/usr/bin/env python3
import os, json, time, urllib.request
from datetime import datetime, timezone

SUPABASE_URL = "https://vbqbbziqleymxcyesmky.supabase.co"
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "sb_secret_lIbl-DBgdnrt_fejgJjKqg_qR62SVEm")

def push_health():
    try:
        data = {
            "device": "Samsung-TCC",
            "last_seen": datetime.now(timezone.utc).isoformat(),
            "status": "online",
            "battery": os.popen("termux-battery-status").read().strip()
        }
        req = urllib.request.Request(
            f"{SUPABASE_URL}/rest/v1/device_state?device=eq.Samsung-TCC",
            data=json.dumps(data).encode(),
            headers={
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}",
                "Content-Type": "application/json",
                "Prefer": "resolution=merge-duplicates"
            },
            method="POST"
        )
        with urllib.request.urlopen(req) as res:
            print(f"Health pushed: {res.status}")
    except Exception as e:
        print(f"Push failed: {e}")

if __name__ == "__main__":
    push_health()
