#!/usr/bin/env python3
"""
TCC Bridge v6.1.0 — BULLETPROOF EDITION (KAEL MOD)
Permanent phone control HTTP server for Termux.
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
VERSION = "6.1.0"
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

def get_battery():
    try:
        res = subprocess.run("termux-battery-status", shell=True, capture_output=True, text=True)
        return json.loads(res.stdout)
    except: return {"percentage": -1, "status": "UNKNOWN"}

class BridgeHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        log.info("%s - %s" % (self.client_address[0], format%args))

    def do_GET(self):
        if self.path == "/health":
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            status = {
                "status": "online",
                "version": VERSION,
                "uptime": get_uptime(),
                "battery": get_battery(),
                "timestamp": time.time()
            }
            self.wfile.write(json.dumps(status).encode())
            return

        # Simple auth check for other endpoints
        auth_header = self.headers.get('Authorization')
        if not auth_header or auth_header != f"Bearer {AUTH_TOKEN}":
            self.send_response(401)
            self.end_headers()
            return

        if self.path == "/":
            self.send_response(200)
            self.send_header("Content-type", "text/plain")
            self.end_headers()
            self.wfile.write(f"TCC Bridge {VERSION} Online".encode())
            return

    def do_POST(self):
        auth_header = self.headers.get('Authorization')
        if not auth_header or auth_header != f"Bearer {AUTH_TOKEN}":
            self.send_response(401)
            self.end_headers()
            return

        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode()
        
        try:
            data = json.loads(body)
            cmd = data.get("command")
            
            if self.path == "/exec":
                res = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
                output = {"stdout": res.stdout, "stderr": res.stderr, "code": res.returncode}
                self.send_response(200)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(output).encode())
                
            elif self.path == "/toast":
                subprocess.run(f"termux-toast '{cmd}'", shell=True)
                self.send_response(200)
                self.end_headers()
                
            elif self.path == "/speak":
                subprocess.run(f"termux-tts-speak '{cmd}'", shell=True)
                self.send_response(200)
                self.end_headers()
                
            else:
                self.send_response(404)
                self.end_headers()
                
        except Exception as e:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(str(e).encode())

def run_server():
    server = HTTPServer(('0.0.0.0', PORT), BridgeHandler)
    log.info(f"Starting Bridge v{VERSION} on port {PORT}...")
    ntfy(f"Bridge v{VERSION} started on port {PORT}. Uptime reset.", "Bridge Online", priority=4, tags=["rocket", "check"])
    try:
        server.serve_forever()
    except Exception as e:
        err = traceback.format_exc()
        log.error(f"Server crash: {err}")
        ntfy(f"Bridge crashed! Error: {str(e)}", "Bridge CRASH", priority=5, tags=["warning", "skull"])
        sys.exit(1)

if __name__ == "__main__":
    # Signal handlers for clean exit
    def signal_handler(sig, frame):
        log.info("Shutting down...")
        ntfy("Bridge shutting down gracefully.", "Bridge Offline", priority=3, tags=["zzz"])
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    run_server()
