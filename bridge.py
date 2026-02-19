#!/usr/bin/env python3
"""
bridge.py v7.0.0 â TCC Bulletproof Bridge
God Builder: Kael

Resilient Bridge with multi-endpoint command handling.
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

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("TCC-Bridge")

class BridgeHandler(BaseHTTPRequestHandler):
    def _send_json(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/health":
            self._send_json({
                "status": "online",
                "version": "7.0.0",
                "timestamp": datetime.now().isoformat(),
                "uptime": time.time() - start_time
            })
        else:
            self._send_json({"error": "Not Found"}, 404)

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        data = json.loads(post_data.decode()) if post_data else {}
        
        parsed = urlparse(self.path)
        endpoint = parsed.path.strip("/")
        
        logger.info(f"Command received: {endpoint}")
        
        try:
            if endpoint == "exec":
                cmd = data.get("command")
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
                self._send_json({"stdout": result.stdout, "stderr": result.stderr, "code": result.returncode})
            
            elif endpoint == "speak":
                text = data.get("text", "No text provided")
                subprocess.run(["termux-tts-speak", text])
                self._send_json({"status": "speaking"})
                
            elif endpoint == "vibrate":
                duration = data.get("duration", 500)
                subprocess.run(["termux-vibrate", "-d", str(duration)])
                self._send_json({"status": "vibrating"})
                
            elif endpoint == "toast":
                text = data.get("text", "Hello from TCC")
                subprocess.run(["termux-toast", text])
                self._send_json({"status": "toasted"})
                
            elif endpoint == "notification":
                title = data.get("title", "TCC Alert")
                content = data.get("content", "Message received")
                subprocess.run(["termux-notification", "-t", title, "-c", content])
                self._send_json({"status": "notified"})
                
            elif endpoint == "write":
                path = os.path.expanduser(data.get("path"))
                content = data.get("content", "")
                with open(path, "w") as f:
                    f.write(content)
                self._send_json({"status": "written", "path": path})
                
            elif endpoint == "read":
                path = os.path.expanduser(data.get("path"))
                if os.path.exists(path):
                    with open(path, "r") as f:
                        content = f.read()
                    self._send_json({"content": content})
                else:
                    self._send_json({"error": "File not found"}, 404)
            
            else:
                self._send_json({"error": "Unknown endpoint"}, 404)
                
        except Exception as e:
            logger.error(traceback.format_exc())
            self._send_json({"error": str(e)}, 500)

def run_server():
    global start_time
    start_time = time.time()
    server = HTTPServer(('0.0.0.0', PORT), BridgeHandler)
    logger.info(f"Bridge V7.0.0 starting on port {PORT}...")
    server.serve_forever()

if __name__ == "__main__":
    run_server()
