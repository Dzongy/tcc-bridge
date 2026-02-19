#!/usr/bin/env python3
"""
TCC Bridge v8.0 — THE ETERNAL BRIDGE
Bulletproof, self-healing, and infinite.
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
NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "tcc-zenith-hive")
VERSION = "8.0.0"
START_TIME = time.time()

os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", 
                    handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler(sys.stderr)])
log = logging.getLogger("bridge")

def ntfy(msg, priority=3, tags=None):
    try:
        req = Request(f"https://ntfy.sh/{NTFY_TOPIC}", data=msg.encode('utf-8'))
        req.add_header("Title", "TCC Bridge V8")
        req.add_header("Priority", str(priority))
        if tags: req.add_header("Tags", ",".join(tags))
        urlopen(req, timeout=5)
    except Exception as e: log.error(f"ntfy failed: {e}")

class BridgeHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args): 
        log.info("%s - - [%s] %s" % (self.client_address[0], self.log_date_time_string(), format%args))
    
    def respond(self, status, data):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/health":
            uptime = time.time() - START_TIME
            return self.respond(200, {
                "status": "online",
                "version": VERSION,
                "uptime_seconds": int(uptime),
                "device": socket.gethostname()
            })
        
        # Auth check for protected routes
        auth = self.headers.get('Authorization')
        if auth != f"Bearer {AUTH_TOKEN}":
            return self.respond(401, {"error": "Unauthorized"})

        if parsed.path == "/exec":
            query = parse_qs(parsed.query)
            cmd = query.get('cmd', [None])[0]
            if not cmd: return self.respond(400, {"error": "No command provided"})
            try:
                result = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT, timeout=15)
                return self.respond(200, {"output": result.decode('utf-8')})
            except Exception as e:
                return self.respond(500, {"error": str(e)})
        
        self.respond(404, {"error": "Not found"})

def run_server():
    server = HTTPServer(('0.0.0.0', PORT), BridgeHandler)
    log.info(f"Bridge V8 started on port {PORT}")
    ntfy("🚀 Bridge V8 is ONLINE", priority=4, tags=["rocket", "white_check_mark"])
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()

if __name__ == "__main__":
    run_server()
