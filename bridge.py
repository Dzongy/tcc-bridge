#!/usr/bin/env python3
"""
TCC Bridge v5.0 — THE PERMANENT BRIDGE
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
NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "tcc-zenith-hive")
VERSION = "5.0.0"
START_TIME = time.time()

os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", 
                    handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler(sys.stderr)])
log = logging.getLogger("bridge")

def ntfy(msg, priority=3, tags=None):
    try:
        req = Request(f"https://ntfy.sh/{NTFY_TOPIC}", data=msg.encode('utf-8'))
        req.add_header("Title", "TCC Bridge V5")
        req.add_header("Priority", str(priority))
        if tags: req.add_header("Tags", ",".join(tags))
        urlopen(req, timeout=5)
    except Exception as e: log.error(f"ntfy failed: {e}")

class BridgeHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args): 
        log.info("%s - - [%s] %s" % (self.client_address[0], self.log_date_time_string(), format%args))
    
    def _send_response(self, code, data, content_type="application/json"):
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        if isinstance(data, (dict, list)):
            self.wfile.write(json.dumps(data).encode('utf-8'))
        else:
            self.wfile.write(str(data).encode('utf-8'))

    def do_GET(self):
        parsed_path = urlparse(self.path)
        if parsed_path.path == "/health":
            self._send_response(200, {"status": "ok", "version": VERSION, "uptime": time.time() - START_TIME})
        elif parsed_path.path == "/":
            self._send_response(200, "TCC Bridge V5 Active", "text/plain")
        else:
            self._send_response(404, {"error": "Not Found"})

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode('utf-8')
        try:
            data = json.loads(body) if body else {}
        except:
            data = {}

        # Auth Check
        token = self.headers.get("Authorization") or data.get("auth")
        if token != AUTH_TOKEN and token != f"Bearer {AUTH_TOKEN}":
            log.warning(f"Unauthorized access attempt from {self.client_address[0]}")
            return self._send_response(401, {"error": "Unauthorized"})

        path = urlparse(self.path).path
        
        try:
            if path == "/exec":
                cmd = data.get("command")
                if not cmd: return self._send_response(400, {"error": "Missing command"})
                res = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
                self._send_response(200, {"stdout": res.stdout, "stderr": res.stderr, "code": res.returncode})
            
            elif path == "/toast":
                msg = data.get("message", "")
                subprocess.run(f"termux-toast -c white -b black '{msg}'", shell=True)
                self._send_response(200, {"status": "sent"})

            elif path == "/vibrate":
                dur = data.get("duration", 500)
                subprocess.run(f"termux-vibrate -d {dur}", shell=True)
                self._send_response(200, {"status": "vibrated"})

            elif path == "/speak":
                text = data.get("text", "")
                subprocess.run(f"termux-tts-speak '{text}'", shell=True)
                self._send_response(200, {"status": "speaking"})

            elif path == "/write_file":
                filepath = os.path.expanduser(data.get("path", ""))
                content = data.get("content", "")
                os.makedirs(os.path.dirname(filepath), exist_ok=True)
                with open(filepath, "w") as f: f.write(content)
                self._send_response(200, {"status": "written", "path": filepath})

            else:
                self._send_response(404, {"error": "Endpoint not found"})
        except Exception as e:
            log.error(f"Error handling {path}: {traceback.format_exc()}")
            self._send_response(500, {"error": str(e)})

def run_server():
    server = HTTPServer(('', PORT), BridgeHandler)
    log.info(f"Starting Bridge V5 on port {PORT}...")
    ntfy("Bridge V5 Started 🚀", tags=["rocket", "link"])
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        log.info("Bridge stopped.")

if __name__ == "__main__":
    run_server()
