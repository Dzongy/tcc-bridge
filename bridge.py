#!/usr/bin/env python3
"""
TCC Bridge v6.0 - THE SOVEREIGN EDITION
Built by KAEL for Commander.
Merged Lineage: v2.2 + v5.3.0 "Bulletproof"
"""

import json
import logging
import os
import subprocess
import sys
import threading
import time
import socket
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.request import Request, urlopen

# --- CONFIG ---
AUTH_TOKEN   = os.environ.get("BRIDGE_AUTH",    "amos-bridge-2026")
PORT         = int(os.environ.get("BRIDGE_PORT", "8080"))
SUPABASE_URL = "https://vbqbbziqleymxcyesmky.supabase.co"
SUPABASE_KEY = "sb_secret_lIbl-DBgdnrt_fejgJjKqg_qR62SVEm"
NTFY_TOPIC   = "tcc-zenith-hive"
DEVICE_ID    = "amos-arms"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.FileHandler(os.path.expanduser("~/bridge.log")), logging.StreamHandler(sys.stderr)]
)
log = logging.getLogger("bridge")

def ntfy(msg, title="Bridge V6", priority=3):
    try:
        req = Request(f"https://ntfy.sh/{NTFY_TOPIC}", data=msg.encode())
        req.add_header("Title", title); req.add_header("Priority", str(priority))
        urlopen(req)
    except: pass

def push_state():
    while True:
        try:
            bat = subprocess.check_output(["termux-battery-status"], encoding='utf-8')
            state = {"device_id": DEVICE_ID, "battery": json.loads(bat).get("percentage"), "timestamp": "now()", "raw_output": "Bridge V6 ONLINE"}
            req = Request(f"{SUPABASE_URL}/rest/v1/device_state", data=json.dumps(state).encode(), method='POST')
            for k, v in {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}", "Content-Type": "application/json", "Prefer": "resolution=merge-duplicates"}.items(): req.add_header(k, v)
            urlopen(req)
        except: pass
        time.sleep(300)

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/health':
            self.send_response(200); self.end_headers()
            self.wfile.write(json.dumps({"status": "ok", "version": "6.0.0"}).encode())
    def do_POST(self):
        self.send_response(200); self.end_headers()
        self.wfile.write(b'{"status":"ok"}')

if __name__ == "__main__":
    ntfy("Bridge V6 Sovereign Online", priority=4)
    threading.Thread(target=push_state, daemon=True).start()
    HTTPServer(('', PORT), Handler).serve_forever()
