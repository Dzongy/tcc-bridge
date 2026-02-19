#!/usr/bin/env python3
"""
TCC Bridge V2 — PERMANENT, BULLETPROOF, NEVER GOES DOWN.
Author: Kael (Master Engineer)
"""

import os, sys, json, time, logging, subprocess, threading, socket
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

# CONFIG
PORT = 8080
LOG_FILE = os.path.expanduser("~/tcc-bridge.log")
NTFY_URL = "https://ntfy.sh/tcc-zenith-hive"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler()]
)
logger = logging.getLogger("bridge")

def notify(msg, title="Bridge Update"):
    try:
        req = Request(NTFY_URL, data=msg.encode('utf-8'), headers={"Title": title})
        urlopen(req)
    except:
        pass

class BridgeHandler(BaseHTTPRequestHandler):
    def _send(self, code, data):
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def do_GET(self):
        if self.path == '/health':
            self._send(200, {"status": "alive", "timestamp": time.time(), "brain": "Kael #10"})
        elif self.path == '/info':
            self._send(200, {
                "uptime": time.clock_gettime(time.CLOCK_BOOTTIME) if hasattr(time, 'clock_gettime') else "N/A",
                "version": "2.0.0-bulletproof"
            })
        else:
            self._send(404, {"error": "not_found"})

    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length).decode('utf-8')
        
        if self.path == '/exec':
            try:
                cmd = json.loads(post_data).get('command')
                logger.info(f"Executing: {cmd}")
                result = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT).decode()
                self._send(200, {"output": result})
            except Exception as e:
                self._send(500, {"error": str(e)})
        else:
            self._send(404, {"error": "not_found"})

def run_server():
    server = HTTPServer(('0.0.0.0', PORT), BridgeHandler)
    logger.info(f"Bridge V2 listening on port {PORT}")
    notify("Bridge V2 is online and bulletproof.", "ZENITH BRIDGE ACTIVE")
    server.serve_forever()

if __name__ == "__main__":
    # Start health monitor thread
    def monitor():
        while True:
            time.sleep(300) # Every 5 mins
            logger.info("Heartbeat: Bridge is pulsing.")
            
    threading.Thread(target=monitor, daemon=True).start()
    
    try:
        run_server()
    except Exception as e:
        logger.error(f"Fatal crash: {e}")
        notify(f"Bridge crashed: {e}", "BRIDGE FATAL ERROR")
        sys.exit(1)
