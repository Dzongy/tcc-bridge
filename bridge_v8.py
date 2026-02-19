#!/usr/bin/env python3
"""
TCC Bridge v8.1.0 — THE PERMANENT BRIDGE
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
VERSION = "8.1.0"
START_TIME = time.time()

os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", 
                    handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler(sys.stderr)])
log = logging.getLogger("bridge")

def ntfy(msg, priority=3, tags=None, title="TCC Bridge V8"):
    try:
        req = Request(f"https://ntfy.sh/{NTFY_TOPIC}", data=msg.encode('utf-8'))
        req.add_header("Title", title)
        req.add_header("Priority", str(priority))
        if tags: req.add_header("Tags", ",".join(tags))
        urlopen(req, timeout=10)
    except Exception as e: log.error(f"ntfy failed: {e}")

class BridgeHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args): 
        log.info("%s - - [%s] %s" % (self.client_address[0], self.log_date_time_string(), format%args))
    
    def send_success(self, data):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps({"success": True, "result": data}).encode('utf-8'))

    def send_error(self, message, code=400):
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps({"success": False, "error": message}).encode('utf-8'))

    def do_GET(self):
        url_path = urlparse(self.path).path
        params = parse_qs(urlparse(self.path).query)
        
        if url_path == '/health':
            uptime = time.time() - START_TIME
            return self.send_success({
                "status": "online",
                "version": VERSION,
                "uptime_seconds": int(uptime),
                "device": "Samsung-TCC"
            })
        
        auth = self.headers.get('Authorization') or params.get('auth', [None])[0]
        if auth != AUTH_TOKEN: return self.send_error("Unauthorized", 401)

        if url_path == '/exec':
            cmd = params.get('cmd', [None])[0]
            if not cmd: return self.send_error("No command")
            try:
                res = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT, timeout=30).decode('utf-8')
                self.send_success(res)
            except Exception as e: self.send_error(str(e))
        elif url_path == '/toast':
            msg = params.get('msg', ["Hello"])[0]
            os.system(f"termux-toast '{msg}'")
            self.send_success("Toast sent")
        elif url_path == '/speak':
            msg = params.get('msg', ["Hello"])[0]
            os.system(f"termux-tts-speak '{msg}'")
            self.send_success("TTS started")
        else:
            self.send_error("Not found", 404)

def run_server():
    server = HTTPServer(('0.0.0.0', PORT), BridgeHandler)
    log.info(f"Bridge V{VERSION} listening on port {PORT}")
    ntfy(f"Bridge V{VERSION} is ONLINE at {PUBLIC_URL}", tags=["rocket", "white_check_mark"])
    server.serve_forever()

if __name__ == "__main__":
    try:
        run_server()
    except Exception as e:
        log.error(f"Bridge crashed: {traceback.format_exc()}")
        ntfy(f"Bridge CRASHED: {e}", priority=5, tags=["warning", "skull"])
        sys.exit(1)
