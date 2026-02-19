#!/usr/bin/env python3
"""
TCC Bridge v7.0 — THE BULLETPROOF BRIDGE
One-tap permanent phone control for Termux.
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
VERSION = "7.0.0"
START_TIME = time.time()

os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", 
                    handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler(sys.stderr)])
log = logging.getLogger("bridge")

def ntfy(msg, priority=3, tags=None):
    try:
        req = Request(f"https://ntfy.sh/{NTFY_TOPIC}", data=msg.encode('utf-8'))
        req.add_header("Title", "TCC Bridge V7")
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
        path = parsed.path
        params = parse_qs(parsed.query)
        
        # Auth
        token = params.get('auth', [None])[0] or self.headers.get('Authorization')
        if token and token.startswith('Bearer '): token = token[7:]
        
        if path == "/health":
            return self.respond(200, {"status": "ok", "version": VERSION, "uptime": time.time() - START_TIME})

        if token != AUTH_TOKEN:
            return self.respond(401, {"error": "Unauthorized"})

        if path == "/status":
            return self.respond(200, {
                "version": VERSION,
                "uptime": time.time() - START_TIME,
                "port": PORT,
                "hostname": socket.gethostname()
            })

        self.respond(404, {"error": "Not Found"})

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        
        # Auth
        token = self.headers.get('Authorization')
        if token and token.startswith('Bearer '): token = token[7:]
        if token != AUTH_TOKEN:
            return self.respond(401, {"error": "Unauthorized"})

        try:
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode('utf-8')
            data = json.loads(body) if body else {}
        except:
            return self.respond(400, {"error": "Invalid JSON"})

        if path == "/exec":
            cmd = data.get("cmd")
            if not cmd: return self.respond(400, {"error": "No command"})
            try:
                result = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT, timeout=30)
                return self.respond(200, {"output": result.decode('utf-8')})
            except subprocess.CalledProcessError as e:
                return self.respond(500, {"error": e.output.decode('utf-8')})
            except Exception as e:
                return self.respond(500, {"error": str(e)})

        if path == "/toast":
            msg = data.get("msg", "TCC Hello")
            subprocess.run(f"termux-toast '{msg}'", shell=True)
            return self.respond(200, {"status": "sent"})

        self.respond(404, {"error": "Not Found"})

def run_server():
    server = HTTPServer(('0.0.0.0', PORT), BridgeHandler)
    log.info(f"Bridge V7 starting on port {PORT}")
    ntfy("Bridge V7 Online", priority=4, tags=["rocket", "check"])
    server.serve_forever()

if __name__ == "__main__":
    run_server()
