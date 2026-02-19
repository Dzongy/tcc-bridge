#!/usr/bin/env python3
"""
TCC Bridge V2 â PERMANENT, BULLETPROOF, NEVER GOES DOWN.
Author: Kael (Master Engineer)
"""

import os, sys, json, time, logging, subprocess, threading
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
    except: pass

class BridgeHandler(BaseHTTPRequestHandler):
    def _send(self, code, data):
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def do_GET(self):
        if self.path == '/health':
            self._send(200, {"status": "ok", "uptime": time.time() - start_time})
        elif self.path == '/state':
            # This would normally be handled by state-push.py but bridge can also return it
            self._send(200, {"status": "active", "bridge": "v2.1"})
        else:
            self._send(404, {"error": "Not Found"})

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode()
        try:
            data = json.loads(body)
            if self.path == '/exec':
                cmd = data.get('command')
                logger.info(f"Executing: {cmd}")
                res = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT).decode()
                self._send(200, {"output": res})
            elif self.path == '/toast':
                msg = data.get('message', '')
                subprocess.run(f"termux-toast '{msg}'", shell=True)
                self._send(200, {"status": "sent"})
            elif self.path == '/vibrate':
                dur = data.get('duration', 500)
                subprocess.run(f"termux-vibrate -d {dur}", shell=True)
                self._send(200, {"status": "vibrated"})
            else:
                self._send(404, {"error": "Path not supported"})
        except Exception as e:
            logger.error(f"Error: {e}")
            self._send(500, {"error": str(e)})

start_time = time.time()
if __name__ == "__main__":
    logger.info(f"Bridge V2 starting on port {PORT}")
    notify("Bridge V2 starting up...", "Status: Online")
    server = HTTPServer(('0.0.0.0', PORT), BridgeHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Stopping...")
        notify("Bridge V2 shutting down.", "Status: Offline")
        server.server_close()
