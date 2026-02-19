#!/usr/bin/env python3
"""
TCC Bridge v7.0.0 — THE SINGULARITY BRIDGE
Bulletproof, self-healing, permanent connection.
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

class BridgeHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        log.info("%s - %s" % (self.client_address[0], format%args))

    def do_GET(self):
        if self.path == "/health":
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            stats = {
                "status": "online",
                "version": VERSION,
                "uptime": int(time.time() - START_TIME),
                "battery": self.get_battery(),
                "process": "pm2-managed"
            }
            self.wfile.write(json.dumps(stats).encode())
        else:
            self.send_error(404)

    def get_battery(self):
        try:
            res = subprocess.run("termux-battery-status", shell=True, capture_output=True, text=True)
            return json.loads(res.stdout)
        except: return {"percentage": -1}

def run_server():
    server = HTTPServer(('0.0.0.0', PORT), BridgeHandler)
    log.info(f"Bridge v{VERSION} starting on port {PORT}...")
    ntfy(f"Bridge v{VERSION} online at port {PORT}", tags=["rocket", "link"])
    server.serve_forever()

if __name__ == "__main__":
    run_server()
