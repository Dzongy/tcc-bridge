#!/usr/bin/env python3
"""
TCC Bridge v7.0.0 — KAEL GOD BUILDER EDITION
Bulletproof, Permanent, Sovereign.
"""
import subprocess, json, os, sys, base64, socket, signal, logging, time, threading, traceback
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.request import Request, urlopen
from urllib.error import URLError
from urllib.parse import parse_qs, urlparse

# -- Config --
AUTH_TOKEN = os.environ.get("BRIDGE_AUTH", "amos-bridge-2026")
PORT = int(os.environ.get("BRIDGE_PORT", "8080"))
LOG_FILE = os.path.expanduser("~/bridge.log")
NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "tcc-zenith-hive")
VERSION = "7.0.0"
START_TIME = time.time()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler(sys.stderr)],
)
log = logging.getLogger("bridge")

def ntfy(msg, title="Bridge Update", priority=3, tags=[]):
    try:
        data = json.dumps({"topic": NTFY_TOPIC, "title": title, "message": msg, "priority": priority, "tags": tags}).encode()
        req = Request("https://ntfy.sh", data=data, method="POST")
        urlopen(req, timeout=5)
    except: pass

def get_uptime():
    return str(int(time.time() - START_TIME))

class BridgeHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/health":
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            status = {
                "status": "online",
                "version": VERSION,
                "uptime": get_uptime(),
                "timestamp": time.time()
            }
            self.wfile.write(json.dumps(status).encode())
            return
        
        # Auth check for other endpoints
        auth = self.headers.get("Authorization")
        if auth != f"Bearer {AUTH_TOKEN}":
            self.send_response(401)
            self.end_headers()
            return

        query = parse_qs(urlparse(self.path).query)
        endpoint = urlparse(self.path).path

        if endpoint == "/exec":
            cmd = query.get("cmd", [""])[0]
            if not cmd:
                self.send_response(400)
                self.end_headers()
                return
            try:
                res = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
                self.send_response(200)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"stdout": res.stdout, "stderr": res.stderr, "code": res.returncode}).encode())
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(str(e).encode())
        
        elif endpoint == "/toast":
            msg = query.get("msg", ["Hello"])[0]
            subprocess.run(f"termux-toast -c white -b black '{msg}'", shell=True)
            self.send_response(200)
            self.end_headers()
            
        elif endpoint == "/state-push":
            # Trigger state-push.py manually
            subprocess.Popen(["python3", "state-push.py"], cwd=os.getcwd())
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"State push triggered")

        else:
            self.send_response(404)
            self.end_headers()

def run_server():
    server = HTTPServer(("0.0.0.0", PORT), BridgeHandler)
    log.info(f"Bridge v{VERSION} starting on port {PORT}")
    ntfy(f"Bridge v{VERSION} is UP and SOVEREIGN.", title="Bridge Online", tags=["rocket", "shield"])
    server.serve_forever()

if __name__ == "__main__":
    try:
        run_server()
    except Exception as e:
        log.error(f"Fatal error: {e}")
        ntfy(f"Bridge CRASHED: {e}", title="Bridge Alert", priority=5, tags=["warning", "skull"])
        sys.exit(1)
