#!/usr/bin/env python3
"""
TCC Bridge V2.1 — PERMANENT & BULLETPROOF
Author: KAEL (God Builder)
Version: 2.1.0
Last Modified: Feb 19, 2026
"""

import os, sys, json, time, signal, socket, logging, threading, traceback, subprocess
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
from urllib.parse import parse_qs, urlparse
from datetime import datetime, timezone

# --- CONFIG ---
PORT = 8080
LOG_FILE = os.path.expanduser("~/tcc/logs/bridge.log")
NTFY_TOPIC = "tcc-zenith-hive"
VERSION = "2.1.0"
START_TIME = time.time()
SUPABASE_URL = "https://vbqbbziqleymxcyesmky.supabase.co"
SUPABASE_KEY = "sb_secret_lIbl-DBgdnrt_fejgJjKqg_qR62SVEm" # Service role key from source

os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler()]
)

def ntfy(msg, priority=3, tags=["robot"]):
    try:
        req = Request(f"https://ntfy.sh/{NTFY_TOPIC}", data=msg.encode('utf-8'))
        req.add_header("Title", "Bridge V2 Health")
        req.add_header("Priority", str(priority))
        req.add_header("Tags", ",".join(tags))
        urlopen(req, timeout=5)
    except Exception as e:
        logging.error(f"ntfy failed: {e}")

class BridgeHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            data = {
                "status": "alive",
                "version": VERSION,
                "uptime": time.time() - START_TIME,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            self.wfile.write(json.dumps(data).encode())
        else:
            self.send_error(404)

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode('utf-8')
        try:
            data = json.loads(body)
        except:
            self.send_error(400, "Invalid JSON")
            return

        command = data.get("command")
        logging.info(f"Command received: {command}")

        result = {"success": False, "error": "Unknown command"}

        if command == "toast":
            msg = data.get("message", "Bridge ping")
            subprocess.run(["termux-toast", msg])
            result = {"success": True}
        elif command == "speak":
            msg = data.get("message", "Bridge alert")
            subprocess.run(["termux-tts-speak", msg])
            result = {"success": True}
        elif command == "vibrate":
            subprocess.run(["termux-vibrate"])
            result = {"success": True}
        elif command == "exec":
            cmd = data.get("cmd")
            res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            result = {"success": True, "stdout": res.stdout, "stderr": res.stderr}
        elif command == "write_file":
            path = os.path.expanduser(data.get("path"))
            content = data.get("content")
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w") as f:
                f.write(content)
            result = {"success": True}
        
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(result).encode())

def run_server():
    server = HTTPServer(('0.0.0.0', PORT), BridgeHandler)
    logging.info(f"Bridge V2.1 starting on port {PORT}")
    ntfy(f"Bridge V2.1 ONLINE. Port: {PORT}. Uptime: 0s", priority=5, tags=["rocket", "white_check_mark"])
    server.serve_forever()

if __name__ == "__main__":
    try:
        run_server()
    except Exception as e:
        logging.critical(f"Bridge CRASHED: {e}")
        ntfy(f"Bridge V2.1 CRASHED: {e}", priority=5, tags=["warning", "skull"])
        sys.exit(1)
