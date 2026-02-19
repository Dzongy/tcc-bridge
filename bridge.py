#!/usr/bin/env python3
"""
TCC BRIDGE V4.0 — THE PERMANENT BULLETPROOF BRIDGE
Master Engineer: KAEL (God Builder)
Lineage: Zenith / Cosmic-Claw
"""
import os, sys, json, time, logging, subprocess, threading, socket, traceback
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
from urllib.parse import urlparse, parse_qs
from datetime import datetime, timezone

PORT = 8080
NTFY_TOPIC = "tcc-zenith-hive"
SUPABASE_URL = "https://vbqbbziqleymxcyesmky.supabase.co"
SUPABASE_KEY = "sb_secret_lIbl-DBgnrt_fejgJjKqg_qR62SVEm"
DEVICE_ID = "zenith-phone"
TUNNEL_URL = "https://zenith.cosmic-claw.com"
START_TIME = time.time()
LOG_FILE = os.path.expanduser("~/tcc-bridge.log")

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s', handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler()])
logger = logging.getLogger("TCC-Bridge")

def ntfy(msg, priority=3, tags=[]):
    try:
        req = Request(f"https://ntfy.sh/{NTFY_TOPIC}", data=msg.encode('utf-8'))
        req.add_header("Title", "TCC Bridge Alert"); req.add_header("Priority", str(priority)); req.add_header("Tags", ",".join(tags))
        urlopen(req, timeout=5)
    except Exception as e: logger.error(f"ntfy failed: {e}")

def get_device_state():
    state = {"device_id": DEVICE_ID, "timestamp": datetime.now(timezone.utc).isoformat()}
    try:
        batt = json.loads(subprocess.check_output(["termux-battery-status"], timeout=2).decode())
        state["battery"] = batt.get("percentage"); state["plugged"] = batt.get("status")
    except: state["battery"] = -1
    try:
        state["uptime_sys"] = subprocess.check_output(["uptime", "-p"], timeout=2).decode().strip()
        state["bridge_uptime"] = int(time.time() - START_TIME)
    except: pass
    return state

def push_to_supabase(data):
    try:
        url = f"{SUPABASE_URL}/rest/v1/device_state"
        req = Request(url, method="POST", data=json.dumps(data).encode())
        req.add_header("apikey", SUPABASE_KEY); req.add_header("Authorization", f"Bearer {SUPABASE_KEY}"); req.add_header("Content-Type", "application/json"); req.add_header("Prefer", "resolution=merge-duplicates")
        with urlopen(req, timeout=10) as f: return f.status in (200, 201)
    except Exception as e: logger.error(f"Supabase push failed: {e}"); return False

class BridgeHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args): return
    def send_json(self, data, status=200):
        self.send_response(status); self.send_header("Content-Type", "application/json"); self.send_header("Access-Control-Allow-Origin", "*"); self.end_headers()
        self.wfile.write(json.dumps(data).encode())
    def do_GET(self):
        parsed = urlparse(self.path); path = parsed.path; params = {k: v[0] for k, v in parse_qs(parsed.query).items()}
        if path == "/health": self.send_json({"status": "ok", "uptime": time.time() - START_TIME, "device": DEVICE_ID})
        elif path == "/state": self.send_json(get_device_state())
        elif path == "/toast": subprocess.run(["termux-toast", params.get("text", "Hello")]); self.send_json({"status": "sent"})
        elif path == "/vibrate": subprocess.run(["termux-vibrate", "-d", params.get("duration", "500")]); self.send_json({"status": "vibrating"})
        elif path == "/speak": subprocess.run(["termux-tts-speak", params.get("text", "System Operational")]); self.send_json({"status": "speaking"})
        else: self.send_json({"error": "not_found"}, 404)
    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0)); body = self.rfile.read(content_length).decode(); parsed = urlparse(self.path)
        if parsed.path == "/exec":
            try:
                data = json.loads(body); cmd = data.get("command")
                if not cmd: return self.send_json({"error": "no_command"}, 400)
                res = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
                self.send_json({"stdout": res.stdout, "stderr": res.stderr, "code": res.returncode})
            except Exception as e: self.send_json({"error": str(e)}, 500)
        else: self.send_json({"error": "not_found"}, 404)

def heartbeat_loop():
    while True:
        state = get_device_state(); push_to_supabase(state)
        try:
            with urlopen(f"{TUNNEL_URL}/health", timeout=10) as f:
                if f.status != 200: ntfy("Public Tunnel Health Check Failed", priority=4, tags=["warning"])
        except: pass
        time.sleep(300)

if __name__ == "__main__":
    threading.Thread(target=heartbeat_loop, daemon=True).start()
    ntfy("Bridge V4.0 Started", priority=4, tags=["rocket", "check"])
    HTTPServer(('0.0.0.0', 8080), BridgeHandler).serve_forever()
