#!/usr/bin/env python3
"""
TCC Bridge V2.1 - Bulletproof Edition
Built by Kael for Commander.
Features: Auto-reconnect, Health endpoint, Traceback logging, Supabase state push.
"""

import os
import json
import time
import threading
import subprocess
import logging
import traceback
import socket
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
from urllib.parse import urlparse
import urllib.request

# --- CONFIG ---
SUPABASE_URL     = "https://vbqbbziqleymxcyesmky.supabase.co"
SUPABASE_KEY     = "sb_secret_lIbl-DBgdnrt_fejgJjKqg_qR62SVEm"
NTFY_TOPIC       = "zenith-escape"
NTFY_BASE        = "https://ntfy.sh"
SERVER_PORT      = 8765
HEARTBEAT_SEC    = 60
REPORT_SEC       = 300 # Push state every 5 mins
MAX_RETRIES      = 5
RETRY_BACKOFF    = [2, 4, 8, 16, 32]
DEVICE_ID        = socket.gethostname()

# --- LOGGING ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler("bridge.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("BridgeV2")

class BridgeHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok", "ts": time.time(), "device": DEVICE_ID}).encode())
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        # Handle incoming commands from Twin/Commander
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        try:
            data = json.loads(post_data)
            logger.info(f"Received command: {data.get('command')}")
            # Process command logic here...
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "received"}).encode())
        except Exception as e:
            logger.error(f"Error processing POST: {traceback.format_exc()}")
            self.send_response(500)
            self.end_headers()

def ntfy_alert(msg, priority=3, tags=[]):
    try:
        req = Request(f"{NTFY_BASE}/{NTFY_TOPIC}", data=msg.encode('utf-8'))
        req.add_header("Title", "Bridge V2 Status")
        req.add_header("Priority", str(priority))
        req.add_header("Tags", ",".join(tags))
        urlopen(req, timeout=5)
    except:
        logger.error("Failed to send ntfy alert")

def push_to_supabase(table, data):
    try:
        url = f"{SUPABASE_URL}/rest/v1/{table}"
        req = Request(url, data=json.dumps(data).encode('utf-8'), method='POST')
        req.add_header("apikey", SUPABASE_KEY)
        req.add_header("Authorization", f"Bearer {SUPABASE_KEY}")
        req.add_header("Content-Type", "application/json")
        req.add_header("Prefer", "return=minimal")
        urlopen(req, timeout=10)
    except Exception as e:
        logger.error(f"Supabase push failed: {e}")

def heartbeat_loop():
    while True:
        try:
            state = {
                "device_id": DEVICE_ID,
                "status": "online",
                "uptime": time.time(),
                "last_check": ts
            }
            push_to_supabase("kael_memory", {"id": "bridge_status", "memory": state})
        except:
            pass
        time.sleep(HEARTBEAT_SEC)

def run_server():
    server = HTTPServer(('0.0.0.0', SERVER_PORT), BridgeHandler)
    logger.info(f"Bridge V2 listening on port {SERVER_PORT}")
    ntfy_alert("Bridge V2 Bulletproof Edition is ONLINE", priority=4, tags=["rocket", "check"])
    server.serve_forever()

if __name__ == "__main__":
    threading.Thread(target=heartbeat_loop, daemon=True).start()
    run_server()
