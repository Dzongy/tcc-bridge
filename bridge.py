#!/usr/bin/env python3
"""
TCC Bridge V6.1 - THE BULLETPROOF EDITION
Built by KAEL God Builder for Commander.
Merged Lineage: Xena v2.2 + Kael v5.3.0 + V2 Evolved.
"""

import os
import sys
import json
import time
import signal
import logging
import subprocess
import threading
import socket
import traceback
from datetime import datetime, timezone
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
from urllib.parse import urlparse, parse_qs

# --- CONFIG ---
AUTH_TOKEN   = os.environ.get("BRIDGE_AUTH", "amos-bridge-2026")
PORT         = int(os.environ.get("BRIDGE_PORT", "8765"))
SUPABASE_URL = "https://vbqbbziqleymxcyesmky.supabase.co"
SUPABASE_KEY = "sb_secret_lIbl-DBgdnrt_fejgJjKqg_qR62SVEm"
NTFY_TOPIC   = "tcc-zenith-hive"
DEVICE_ID    = "amos-arms"
LOG_FILE     = os.path.expanduser("~/bridge.log")

# --- LOGGING ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler(sys.stderr)]
)
log = logging.getLogger("bridge")

def ntfy(msg, title="Bridge V6", priority=3):
    try:
        req = Request(f"https://ntfy.sh/{NTFY_TOPIC}", data=msg.encode())
        req.add_header("Title", title)
        req.add_header("Priority", str(priority))
        urlopen(req, timeout=5)
    except: pass

class BridgeHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/health":
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"OK")
            return
        self.send_error(404)

    def do_POST(self):
        auth = self.headers.get("Authorization", "")
        if auth != f"Bearer {AUTH_TOKEN}":
            self.send_error(401, "Unauthorized")
            return

        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        
        try:
            data = json.loads(post_data)
            cmd = data.get("command")
            if not cmd:
                self.send_error(400, "Missing command")
                return
            
            log.info(f"Executing: {cmd}")
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
            
            response = {
                "status": "success" if result.returncode == 0 else "error",
                "stdout": result.stdout,
                "stderr": result.stderr,
                "code": result.returncode
            }
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
            
        except Exception as e:
            log.error(f"Error: {e}")
            self.send_error(500, str(e))

def run_server():
    server = HTTPServer(('0.0.0.0', PORT), BridgeHandler)
    log.info(f"Bridge V6.1 listening on port {PORT}")
    server.serve_forever()

def state_pusher():
    while True:
        try:
            # Get system info
            bat = subprocess.check_output("termux-battery-status", shell=True).decode().strip()
            wifi = subprocess.check_output("termux-wifi-connectioninfo", shell=True).decode().strip()
            
            state = {
                "device_id": DEVICE_ID,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "battery": json.loads(bat),
                "network": json.loads(wifi),
                "status": "online"
            }
            
            headers = {
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}",
                "Content-Type": "application/json",
                "Prefer": "resolution=merge-duplicates"
            }
            
            req = Request(f"{SUPABASE_URL}/rest/v1/device_state", 
                          data=json.dumps(state).encode(), 
                          headers=headers, method="POST")
            urlopen(req, timeout=10)
            log.info("State pushed to Supabase")
        except Exception as e:
            log.error(f"State push failed: {e}")
        time.sleep(300)

if __name__ == "__main__":
    ntfy("Bridge V6.1 Starting - Sovereignty Active", "TCC Bridge", 4)
    threading.Thread(target=state_pusher, daemon=True).start()
    run_server()
