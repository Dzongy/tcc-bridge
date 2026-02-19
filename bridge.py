#!/usr/bin/env python3
# =============================================================================
# TCC Master Bridge v10.0.0
# Permanent, bulletproof bridge for Termux + Cloudflare + Supabase
# =============================================================================

import json
import logging
import os
import subprocess
import sys
import threading
import time
import traceback
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.request import Request, urlopen

# Configuration
VERSION = "10.0.0"
BASE_PORT = 8765
DEVICE_ID = "amos-arms"
SUPABASE_URL = "https://vbqbbziqleymxcyesmky.supabase.co"
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "sb_secret_lIbl-DBgdnrt_fejgJjKqg_qR62SVEm")
NTFY_URL = "https://ntfy.sh/tcc-zenith-hive"

# Logging
LOG_DIR = os.path.expanduser("~/tcc-bridge/logs")
os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler(os.path.join(LOG_DIR, "bridge.log")), logging.StreamHandler(sys.stdout)]
)
log = logging.getLogger("bridge")

def get_battery():
    try:
        res = subprocess.check_output("termux-battery-status", shell=True).decode()
        return json.loads(res)
    except: return {}

def check_health():
    return {
        "status": "online",
        "version": VERSION,
        "device_id": DEVICE_ID,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "battery": get_battery()
    }

class BridgeHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(check_health()).encode())
        else:
            self.send_response(404)
            self.end_headers()

def start_server():
    server = HTTPServer(('0.0.0.0', BASE_PORT), BridgeHandler)
    log.info(f"Bridge v{VERSION} starting on port {BASE_PORT}")
    server.serve_forever()

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--once":
        print(json.dumps(check_health()))
    else:
        start_server()
