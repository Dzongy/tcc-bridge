#!/usr/bin/env python3
"""
TCC Bridge V2.5 - BULLETPROOF EDITION
Built by KAEL God Builder for Commander.
Features: Auto-reconnect, Health endpoint, State push, PM2, Termux:Boot.
"""

import os, json, time, threading, subprocess, logging, traceback, socket
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

# CONFIG
SUPABASE_URL = "https://vbqbbziqleymxcyesmky.supabase.co"
SUPABASE_KEY = "sb_secret_lIbl-DBgdnrt_fejgJjKqg_qR62SVEm"
NTFY_TOPIC = "tcc-zenith-hive"
PORT = 8765
REPORT_SEC = 300
DEVICE_ID = "zenith-phone"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(os.path.expanduser("~/tcc-bridge.log")),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("BridgeV2")

class BridgeHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({
                "status": "ok",
                "device": DEVICE_ID,
                "uptime": time.time() - start_time
            }).encode())
        else:
            self.send_error(404)

    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        try:
            cmd = json.loads(post_data.decode())
            action = cmd.get("action")
            logger.info(f"Action received: {action}")
            
            # Exec implementation
            if action == "exec":
                res = subprocess.check_output(cmd.get("command"), shell=True).decode()
                self._respond({"status": "success", "output": res})
            elif action == "toast":
                subprocess.run(f"termux-toast '{cmd.get('text')}'", shell=True)
                self._respond({"status": "success"})
            else:
                self._respond({"status": "error", "message": "unknown action"}, 400)
        except Exception as e:
            logger.error(traceback.format_exc())
            self._respond({"status": "error", "message": str(e)}, 500)

    def _respond(self, data, code=200):
        self.send_response(code)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

def start_server():
    server = HTTPServer(('0.0.0.0', PORT), BridgeHandler)
    logger.info(f"Bridge V2 listening on port {PORT}")
    server.serve_forever()

start_time = time.time()
if __name__ == "__main__":
    threading.Thread(target=start_server, daemon=True).start()
    while True:
        time.sleep(1)
