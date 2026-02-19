#!/usr/bin/env python3
"""
TCC Bridge v2.1.0 — THE WATCHDOG (KAEL MOD)
Bulletproof state pusher and process monitor.
Pushes to Supabase and ensures bridge/tunnel are alive.
"""
import os, sys, json, time, subprocess, requests, socket, traceback
from datetime import datetime

# -- Config --
SUPABASE_URL = "https://vbqbbziqleymxcyesmky.supabase.co"
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "sb_secret_lIbl-DBgdnrt_fejgJjKqg_qR62SVEm")
DEVICE_ID = "amos-arms"
NTFY_TOPIC = "tcc-zenith-hive"
INTERVAL = 60 # 1 minute
BRIDGE_URL = "http://localhost:8080/health"

class Watchdog:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json",
            "Prefer": "return=minimal"
        })

    def ntfy(self, msg, title="Watchdog Alert", priority=3, tags=[]):
        try:
            requests.post("https://ntfy.sh", 
                data=json.dumps({"topic": NTFY_TOPIC, "title": title, "message": msg, "priority": priority, "tags": tags}),
                timeout=5)
        except: pass

    def get_stats(self):
        stats = {
            "device_id": DEVICE_ID,
            "timestamp": datetime.utcnow().isoformat(),
            "battery": -1,
            "android_version": "Unknown",
            "termux_version": "Unknown",
            "hostname": socket.gethostname(),
            "network": "Unknown"
        }
        try:
            bat = subprocess.run("termux-battery-status", shell=True, capture_output=True, text=True).stdout
            if bat: stats["battery"] = json.loads(bat).get("percentage", -1)
            
            # Additional info
            stats["android_version"] = subprocess.run("getprop ro.build.version.release", shell=True, capture_output=True, text=True).stdout.strip()
            stats["termux_version"] = os.environ.get("TERMUX_VERSION", "Unknown")
            
            # Network info
            net = subprocess.run("termux-telephony-deviceinfo", shell=True, capture_output=True, text=True).stdout
            if net: stats["network"] = net.strip()
            
            stats["raw_output"] = f"Uptime: {subprocess.run('uptime', shell=True, capture_output=True, text=True).stdout.strip()}"
        except: pass
        return stats

    def push_to_supabase(self, stats):
        try:
            # Check if record exists for this device_id to decide update or insert
            # Actually, the schema uses 'id' as PK (int), we should probably just insert a log
            # but 'device_state' seems intended for current state. 
            # I'll try to upsert by device_id if possible, or just post.
            res = self.session.post(f"{SUPABASE_URL}/rest/v1/device_state", json=stats)
            if res.status_code not in [200, 201]:
                print(f"Supabase error: {res.text}")
        except Exception as e:
            print(f"Failed to push to Supabase: {e}")

    def check_processes(self):
        # 1. Check bridge.py
        bridge_alive = False
        try:
            r = requests.get(BRIDGE_URL, timeout=5)
            if r.status_code == 200: bridge_alive = True
        except: pass
        
        if not bridge_alive:
            print("Bridge seems down. Restarting...")
            subprocess.run("pm2 restart tcc-bridge", shell=True)
            self.ntfy("Bridge server was down. Attempted PM2 restart.", "Bridge Recovered", priority=4, tags=["wrench"])

        # 2. Check cloudflared
        cf_running = subprocess.run("pgrep cloudflared", shell=True).returncode == 0
        if not cf_running:
            print("Cloudflared down. Restarting...")
            subprocess.run("pm2 restart cloudflared", shell=True)
            self.ntfy("Cloudflared tunnel was down. Attempted PM2 restart.", "Tunnel Recovered", priority=4, tags=["bridge"])

    def run(self):
        print("Watchdog v2.1.0 starting...")
        self.ntfy("Bridge Watchdog active. Monitoring starts now.", "Watchdog Online", priority=3, tags=["shield"])
        while True:
            try:
                stats = self.get_stats()
                self.push_to_supabase(stats)
                self.check_processes()
            except Exception as e:
                print(f"Loop error: {e}")
            time.sleep(INTERVAL)

if __name__ == "__main__":
    Watchdog().run()
