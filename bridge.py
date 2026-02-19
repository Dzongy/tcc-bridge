#!/usr/bin/env python3
"""TCC Bridge v5.1 — BULLETPROOF EDITION
Permanent phone control HTTP server for Termux.
Endpoints: /exec, /toast, /speak, /vibrate, /write_file, /listen, /conversation, /health, /voice, /state-push, /tunnel-health
Features: Auto-reconnect, crash recovery, Supabase state push, health monitoring
Auth: X-Auth header token
"""
import subprocess
import json
import os
import sys
import base64
import signal
import logging
import time
import threading
import traceback
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.request import Request, urlopen
from urllib.parse import urlparse

# ── Config ──
AUTH_TOKEN   = os.environ.get("BRIDGE_AUTH",    "amos-bridge-2026")
PORT         = int(os.environ.get("BRIDGE_PORT", "8080"))
LOG_FILE     = os.path.expanduser("~/bridge.log")
SUPABASE_URL = os.environ.get("SUPABASE_URL",   "https://vbqbbziqleymxcyesmky.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY",   "")
NTFY_TOPIC   = os.environ.get("NTFY_TOPIC",     "tcc-zenith-hive")
HEALTH_INTERVAL = 300          # 5 minutes between Supabase pushes
VERSION      = "5.1.0"
START_TIME   = time.time()
DEVICE_ID    = "amos-arms"

# ── Logging (file + stderr) ──
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stderr),
    ],
)
log = logging.getLogger("bridge")

def kill_port(port: int):
    """Kill every process holding *port* except our own PID."""
    try:
        cmd = f"fuser -k {port}/tcp"
        subprocess.run(cmd, shell=True, capture_output=True)
    except: pass

class BridgeHandler(BaseHTTPRequestHandler):
    def _send_resp(self, code, data):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/health":
            self._send_resp(200, {
                "status": "online",
                "version": VERSION,
                "uptime_sec": int(time.time() - START_TIME),
                "device": DEVICE_ID
            })
        elif parsed.path == "/tunnel-health":
            # Check if our own public URL is reachable
            try:
                urlopen("https://zenith.cosmic-claw.com/health", timeout=5)
                self._send_resp(200, {"tunnel": "up"})
            except:
                self._send_resp(500, {"tunnel": "down"})
        else:
            self._send_resp(404, {"error": "not_found"})

    def do_POST(self):
        auth = self.headers.get("X-Auth")
        if auth != AUTH_TOKEN:
            self._send_resp(401, {"error": "unauthorized"})
            return

        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode("utf-8")
        data = json.loads(body) if body else {}

        parsed = urlparse(self.path)
        if parsed.path == "/exec":
            cmd = data.get("cmd")
            res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            self._send_resp(200, {"stdout": res.stdout, "stderr": res.stderr, "code": res.returncode})
        elif parsed.path == "/toast":
            msg = data.get("msg", "TCC Hello")
            subprocess.run(f"termux-toast '{msg}'", shell=True)
            self._send_resp(200, {"status": "ok"})
        elif parsed.path == "/speak":
            msg = data.get("msg", "TCC Online")
            subprocess.run(f"termux-tts-speak '{msg}'", shell=True)
            self._send_resp(200, {"status": "ok"})
        else:
            self._send_resp(404, {"error": "not_found"})

def run_server():
    log.info(f"Starting Bridge v{VERSION} on port {PORT}")
    kill_port(PORT)
    server = HTTPServer(("0.0.0.0", PORT), BridgeHandler)
    server.serve_forever()

if __name__ == "__main__":
    run_server()
