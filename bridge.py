#!/usr/bin/env python3
"""
TCC Bridge V2.2 - Bulletproof Edition
Built by Kael for Commander.
Features: Auto-reconnect, Health endpoint, State push to Supabase, PM2 ready.
"""

import os, json, time, threading, subprocess, logging, traceback, socket
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

# --- CONFIG ---
SUPABASE_URL = "https://vbqbbziqleymxcyesmky.supabase.co"
SUPABASE_KEY = "sb_secret_lIbl-DBgdnrt_fejgJjKqg_qR62SVEm"
PORT = 8765
REPORT_SEC = 300
DEVICE_ID = socket.gethostname()

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("BridgeV2")

class BridgeHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok", "device": DEVICE_ID, "time": time.time()}).encode())
        else:
            self.send_response(404)
            self.end_headers()

def push_state():
    while True:
        try:
            state = {
                "device_id": DEVICE_ID,
                "timestamp": time.time(),
                "status": "online"
            }
            req = Request(f"{SUPABASE_URL}/rest/v1/kael_memory", 
                          data=json.dumps(state).encode(),
                          headers={
                              "apikey": SUPABASE_KEY, 
                              "Authorization": f"Bearer {SUPABASE_KEY}", 
                              "Content-Type": "application/json", 
                              "Prefer": "resolution=merge-duplicates"
                          })
            urlopen(req)
            logger.info("State pushed to Supabase")
        except Exception as e:
            logger.error(f"Failed to push state: {e}")
        time.sleep(REPORT_SEC)

def run_server():
    server = HTTPServer(('0.0.0.0', PORT), BridgeHandler)
    logger.info(f"Bridge server starting on port {PORT}")
    server.serve_forever()

if __name__ == "__main__":
    threading.Thread(target=push_state, daemon=True).start()
    run_server()
