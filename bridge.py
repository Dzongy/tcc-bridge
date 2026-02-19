#!/usr/bin/env python3
"""
bridge.py v7.0.0 — TCC Bulletproof Bridge (The Ultimate Version)
God Builder: Kael
Purpose: Full sovereignty bridge for Termux. Handles commands, voice, toast, and health.
"""

import json
import logging
import os
import subprocess
import sys
import threading
import time
import traceback
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

# --- CONFIGURATION ---
PORT = int(os.environ.get("BRIDGE_PORT", 8080))
NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "tcc-zenith-hive")
LOG_PATH = os.path.expanduser("~/bridge.log")
VERSION = "7.0.0"
START_TIME = time.time()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("TCC-Bridge")

def termux_api(command, args=None):
    """Run a Termux API command."""
    try:
        full_cmd = ["termux-" + command]
        if args:
            full_cmd.extend(args)
        logger.info(f"Running Termux API: {' '.join(full_cmd)}")
        result = subprocess.run(full_cmd, capture_output=True, text=True, timeout=10)
        return result.stdout.strip()
    except Exception as e:
        logger.error(f"Termux API failed: {e}")
        return str(e)

class BridgeHandler(BaseHTTPRequestHandler):
    def _send_json(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def do_GET(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        
        if parsed.path == "/health":
            self._send_json({
                "status": "online",
                "version": VERSION,
                "uptime": round(time.time() - START_TIME, 2),
                "timestamp": datetime.now().isoformat(),
                "device": "amos-arms"
            })
        
        elif parsed.path == "/toast":
            msg = params.get("msg", ["Bridge Online"])[0]
            termux_api("toast", [msg])
            self._send_json({"status": "sent", "msg": msg})

        elif parsed.path == "/vibrate":
            duration = params.get("duration", ["500"])[0]
            termux_api("vibrate", ["-d", duration])
            self._send_json({"status": "vibrated", "duration": duration})

        elif parsed.path == "/speak":
            text = params.get("text", ["Hello Commander"])[0]
            termux_api("tts-speak", [text])
            self._send_json({"status": "spoken", "text": text})
            
        else:
            self._send_json({"error": "endpoint not found"}, 404)

    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        parsed = urlparse(self.path)
        
        try:
            data = json.loads(post_data.decode('utf-8'))
        except:
            data = {}

        if parsed.path == "/exec":
            cmd = data.get("cmd")
            if not cmd:
                return self._send_json({"error": "no command provided"}, 400)
            
            try:
                logger.info(f"Executing: {cmd}")
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
                self._send_json({
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "returncode": result.returncode
                })
            except Exception as e:
                self._send_json({"error": str(e)}, 500)

        elif parsed.path == "/write_file":
            path = data.get("path")
            content = data.get("content")
            if not path or content is None:
                return self._send_json({"error": "missing path or content"}, 400)
            
            try:
                full_path = os.path.expanduser(path)
                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                with open(full_path, "w") as f:
                    f.write(content)
                self._send_json({"status": "written", "path": path})
            except Exception as e:
                self._send_json({"error": str(e)}, 500)

        else:
            self._send_json({"error": "endpoint not found"}, 404)

def run_server():
    server_address = ('', PORT)
    httpd = HTTPServer(server_address, BridgeHandler)
    logger.info(f"Bridge v{VERSION} starting on port {PORT}...")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    httpd.server_close()

if __name__ == "__main__":
    # Start a health-reporting thread that pings ntfy on startup
    def report_startup():
        try:
            time.sleep(2)
            msg = f"🚀 TCC Bridge v{VERSION} AWAKENED\nUptime: 0s\nPort: {PORT}"
            subprocess.run(["curl", "-d", msg, f"https://ntfy.sh/{NTFY_TOPIC}"], capture_output=True)
        except:
            pass

    threading.Thread(target=report_startup, daemon=True).start()
    run_server()
