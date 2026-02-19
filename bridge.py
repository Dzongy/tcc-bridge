#!/usr/bin/env python3
"""
TCC Bridge V10.0 — THE ETERNAL BRIDGE (Bulletproof)
Built by KAEL God Builder for Commander.
Features: Health checks, Termux integration, robust command execution.
"""
import os, sys, json, time, logging, subprocess, threading, socket
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# CONFIG
PORT = int(os.environ.get("BRIDGE_PORT", "8765"))
AUTH_TOKEN = os.environ.get("BRIDGE_AUTH", "amos-bridge-2026")
DEVICE_ID = "amos-arms"

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
log = logging.getLogger("bridge")

class BridgeHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "alive", "device": DEVICE_ID, "time": time.time()}).encode())
        else:
            self.send_error(404)

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode()
        try:
            data = json.loads(body)
        except:
            self.send_error(400, "Invalid JSON")
            return

        if data.get("auth") != AUTH_TOKEN:
            self.send_error(401, "Unauthorized")
            return

        path = urlparse(self.path).path
        
        if path == '/exec':
            cmd = data.get("command")
            if not cmd:
                self.send_error(400, "Missing command")
                return
            try:
                output = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT, timeout=30).decode()
                self._send_json({"status": "success", "output": output})
            except subprocess.CalledProcessError as e:
                self._send_json({"status": "error", "output": e.output.decode()}, 500)
            except Exception as e:
                self._send_json({"status": "error", "message": str(e)}, 500)

        elif path == '/toast':
            msg = data.get("message", "Bridge Pulse")
            subprocess.run(f"termux-toast '{msg}'", shell=True)
            self._send_json({"status": "success"})

        elif path == '/speak':
            msg = data.get("message", "Bridge active")
            subprocess.run(f"termux-tts-speak '{msg}'", shell=True)
            self._send_json({"status": "success"})

        else:
            self.send_error(404)

    def _send_json(self, data, code=200):
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

def run_server():
    server = HTTPServer(('0.0.0.0', PORT), BridgeHandler)
    log.info(f"Bridge V10.0 listening on port {PORT}...")
    server.serve_forever()

if __name__ == '__main__':
    run_server()