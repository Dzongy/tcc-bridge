#!/usr/bin/env python3
"""
TCC Bridge v6.0 — THE PERMANENT BRIDGE
Bulletproof phone control HTTP server for Termux.
Survives: Reboots, network drops, process kills, memory cleanup.
"""
import subprocess, json, os, sys, socket, signal, logging, time, threading, traceback
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.request import Request, urlopen
from urllib.error import URLError
from urllib.parse import parse_qs, urlparse

# -- Config --
AUTH_TOKEN = os.environ.get("BRIDGE_AUTH", "amos-bridge-2026")
PORT = int(os.environ.get("BRIDGE_PORT", "8080"))
LOG_FILE = os.path.expanduser("~/tcc/logs/bridge.log")
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://vbqbbziqleymxcyesmky.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")
NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "tcc-zenith-hive")
PUBLIC_URL = os.environ.get("PUBLIC_URL", "https://zenith.cosmic-claw.com")
VERSION = "6.0.0"
START_TIME = time.time()

os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", 
                    handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler(sys.stderr)])
log = logging.getLogger("bridge")

def ntfy(msg, priority=3, tags=None):
    try:
        req = Request(f"https://ntfy.sh/{NTFY_TOPIC}", data=msg.encode('utf-8'))
        req.add_header("Title", "TCC Bridge V6")
        req.add_header("Priority", str(priority))
        if tags: req.add_header("Tags", ",".join(tags))
        urlopen(req)
    except Exception as e: log.error(f"ntfy failed: {e}")

class BridgeHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args): log.info("%s - - [%s] %s" % (self.client_address[0], self.log_date_time_string(), format%args))
    
    def do_GET(self):
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        
        # Public health check (No Auth)
        if path == "/health":
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            uptime = time.time() - START_TIME
            self.wfile.write(json.dumps({"status": "alive", "version": VERSION, "uptime_sec": int(uptime)}).encode())
            return

        # Auth Check
        auth = self.headers.get('Authorization')
        if auth != f"Bearer {AUTH_TOKEN}":
            self.send_response(401)
            self.end_headers()
            return

        if path == "/exec":
            query = parse_qs(parsed_path.query)
            cmd = query.get('cmd', [''])[0]
            if not cmd:
                self.send_response(400)
                self.end_headers()
                return
            try:
                res = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT).decode()
                self.send_response(200)
                self.send_header('Content-Type', 'text/plain')
                self.end_headers()
                self.wfile.write(res.encode())
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(str(e).encode())
        else:
            self.send_response(404)
            self.end_headers()

def run_server():
    server = HTTPServer(('0.0.0.0', PORT), BridgeHandler)
    log.info(f"Bridge V6 started on port {PORT}")
    ntfy("🚀 Bridge Online", priority=4, tags=["rocket", "check"])
    server.serve_forever()

if __name__ == "__main__":
    try:
        run_server()
    except KeyboardInterrupt:
        log.info("Shutdown")
    except Exception as e:
        log.critical(f"Fatal error: {traceback.format_exc()}")
        ntfy(f"⚠️ Bridge Crash: {e}", priority=5, tags=["warning", "skull"])
        sys.exit(1)
