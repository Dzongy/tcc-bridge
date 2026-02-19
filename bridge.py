#!/usr/bin/env python3
"""
TCC Bridge V2 — PERMANENT, BULLETPROOF, NEVER GOES DOWN.
Author: Kael (Master Engineer)
Version: 2.1.0
"""

import os, sys, json, time, signal, logging, subprocess, threading, traceback
from datetime import datetime, timezone
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
from urllib.parse import urlparse, parse_qs

# CONFIG
SERVER_PORT = 8080 # User mentioned :8080 in tunnel context
LOG_FILE = os.path.expanduser("~/tcc-bridge.log")
SUPABASE_URL = "https://vbqbbziqleymxcyesmky.supabase.co"
SUPABASE_KEY = "sb_secret_lIbl-DBgdnrt_fejgJjKqg_qR62SVEm"
NTFY_TOPIC = "tcc-zenith-hive"

# LOGGING
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler()]
)
logger = logging.getLogger("bridge")

class BridgeHandler(BaseHTTPRequestHandler):
    def _send_response(self, code, data):
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_GET(self):
        if self.path == '/health':
            status = {
                "status": "online",
                "version": "2.1.0",
                "uptime": time.time() - start_time,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            self._send_response(200, status)
        else:
            self._send_response(404, {"error": "Not Found"})

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode('utf-8')
        try:
            data = json.loads(body) if body else {}
        except:
            data = {}

        if self.path == '/exec':
            cmd = data.get('cmd')
            if not cmd: return self._send_response(400, {"error": "Missing 'cmd'"})
            try:
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
                self._send_response(200, {"stdout": result.stdout, "stderr": result.stderr, "code": result.returncode})
            except Exception as e:
                self._send_response(500, {"error": str(e)})

        elif self.path == '/toast':
            text = data.get('text', 'Hello from Bridge')
            subprocess.run(f"termux-toast '{text}'", shell=True)
            self._send_response(200, {"status": "ok"})

        elif self.path == '/speak':
            text = data.get('text', '')
            subprocess.run(f"termux-tts-speak '{text}'", shell=True)
            self._send_response(200, {"status": "ok"})

        elif self.path == '/vibrate':
            duration = data.get('duration', 300)
            subprocess.run(f"termux-vibrate -d {duration}", shell=True)
            self._send_response(200, {"status": "ok"})

        elif self.path == '/restart':
            self._send_response(200, {"status": "restarting"})
            def restart():
                time.sleep(1)
                os.execv(sys.executable, ['python3'] + sys.argv)
            threading.Thread(target=restart).start()

        else:
            self._send_response(404, {"error": "Not Found"})

start_time = time.time()
if __name__ == "__main__":
    server = HTTPServer(('0.0.0.0', SERVER_PORT), BridgeHandler)
    logger.info(f"Bridge V2 listening on port {SERVER_PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    server.server_close()
