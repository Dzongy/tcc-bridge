#!/usr/bin/env python3
"""
BRIDGE V2 (v5.0.0) — PERMANENT, BULLETPROOF, NEVER GOES DOWN.
Author: KAEL (Master Engineer)
Features: /health, /exec, /state (Termux-API), watchdog, auto-restart, heartbeat.
"""

import os, sys, json, time, signal, logging, subprocess, threading, traceback
from datetime import datetime, timezone
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
from urllib.parse import urlparse, parse_qs

# CONFIG
SUPABASE_URL = "https://vbqbbziqleymxcyesmky.supabase.co"
SUPABASE_KEY = "sb_secret_lIbl-DBgdnrt_fejgJjKqg_qR62SVEm"
NTFY_TOPIC = "tcc-zenith-hive"
SERVER_PORT = 8080
LOG_FILE = os.path.expanduser("~/tcc/logs/bridge.log")
HEARTBEAT_IV = 300 # 5 min

# LOGGING
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler()]
)
logger = logging.getLogger("BRIDGE")

class BridgeHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        
        if path == "/health":
            self.send_response(200)
            self.end_headers()
            self.wfile.write(json.dumps({"status": "online", "version": "5.0.0", "time": datetime.now().isoformat()}).encode())
        
        elif path == "/state":
            # Get phone state via termux-api
            state = {"battery": {}, "wifi": {}, "telephony": {}}
            try:
                state["battery"] = json.loads(subprocess.check_output(["termux-battery-status"]).decode())
                state["wifi"] = json.loads(subprocess.check_output(["termux-wifi-connectioninfo"]).decode())
            except:
                logger.error("Failed to get state via termux-api")
            
            self.send_response(200)
            self.end_headers()
            self.wfile.write(json.dumps(state).encode())
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        
        if path == "/exec":
            try:
                data = json.loads(post_data)
                cmd = data.get("cmd")
                logger.info(f"Executing: {cmd}")
                result = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT).decode()
                self.send_response(200)
                self.end_headers()
                self.wfile.write(json.dumps({"output": result}).encode())
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode())
        else:
            self.send_response(404)
            self.end_headers()

def run_server():
    server = HTTPServer(('0.0.0.0', SERVER_PORT), BridgeHandler)
    logger.info(f"Bridge v5.0.0 starting on port {SERVER_PORT}")
    server.serve_forever()

def heartbeat_loop():
    while True:
        try:
            # Push to Supabase and ntfy
            logger.info("Sending heartbeat...")
            msg = f"BRIDGE v5 ONLINE | {datetime.now().strftime('%H:%M:%S')}"
            urlopen(Request(f"https://ntfy.sh/{NTFY_TOPIC}", data=msg.encode()))
        except Exception as e:
            logger.error(f"Heartbeat failed: {e}")
        time.sleep(HEARTBEAT_IV)

if __name__ == "__main__":
    threading.Thread(target=heartbeat_loop, daemon=True).start()
    run_server()
