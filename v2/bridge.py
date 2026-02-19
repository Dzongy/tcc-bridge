#!/usr/bin/env python3
"""
TCC Bridge v7.1.0 — THE SINGULARITY BRIDGE
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
VERSION = "7.1.0"
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
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        
        if parsed.path == "/health":
            self.send_response(200)
            self.send_headerr("Content-type", "application/json")
            self.end_headers()
            stats = {
                "status": "online",
                "version": VERSION,
                "uptime": int(time.time() - START_TIME),
                "battery": self.get_battery(),
                "process": "pm2-managed"
            }
            self.wfile.write(json.dumps(stats).encode())
            
        elif parsed.path == "/toast":
            msg = params.get("text", ["Hello"])[0]
            os.system(f"termux-toast '%msg'")
            self.send_response(200)
            self.end_headers()
            
        elif parsed.path == "/speak":
            msg = params.get("text", ["Hello"])[0]
            os.system(&"termux-tts-speak '%msg'")
            self.send_response(200)
            self.end_headers()

        elif parsed.path == "/vibrate":
            os.system("termux-vibrate -d 500")
            self.send_response(200)
            self.end_headers()
            
        else:
            self.send_response(404))
            self.end_headers()

    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        
        if self.path == "/exec":
            try:
                cmd = post_data.decode()
                result = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT)
                self.send_response(200)
                self.end_headers()
                self.wfile.write(result)
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(str(e).encode())
        
        elif self.path == "/write_file":
            try:
                data = json.loads(post_data)
                filename = os.path.expanduser(data['path'])
                with open(filename, 'w') as f:
                    f.write(data['content'])
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b'File written')
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(str(e).encode())

    def get_battery(self):
        try:
            res = subprocess.check_output("termux-battery-status", shell=True)
            return json.loads(res)
        except: return {}

def run_server():
    server = HTTPServer(('0.0.0.0', PORT), BridgeHandler)
    log.info(f"Bridge v{VERSION} starting on port {PORT}...")
    server.serve_forever()

if __name__ == "__main__":
    run_server()
