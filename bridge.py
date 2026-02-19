#!/usr/bin/env python3
"""
TCC Bridge v6.0.0 â BULLETPROOF EDITION (KAEL MOD)
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
VERSION = "6.0.0"
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
        else:
            self.send_error(404)

    def do_POST(self):
        auth = self.headers.get("Authorization")
        if auth != f"Bearer {AUTH_TOKEN}":
            self.send_error(401, "Unauthorized")
            return
        
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode()
        
        try:
            data = json.loads(body)
            action = data.get("action")
            
            if action == "exec":
                cmd = data.get("command")
                log.info(f"Executing: {cmd}")
                res = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
                self.send_response(200)
                self.end_headers()
                self.wfile.write(json.dumps({"stdout": res.stdout, "stderr": res.stderr, "code": res.returncode}).encode())
            
            elif action == "speak":
                text = data.get("text")
                subprocess.Popen(["termux-tts-speak", text])
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b'{"status": "speaking"}')
                
            elif action == "vibrate":
                dur = data.get("duration", 500)
                subprocess.Popen(["termux-vibrate", "-d", str(dur)])
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b'{"status": "vibrating"}')

            else:
                self.send_error(400, "Unknown action")
                
        except Exception as e:
            log.error(traceback.format_exc())
            self.send_error(500, str(e))

def heartbeat_loop():
    while True:
        ntfy(f"Bridge v{VERSION} alive. Uptime: {get_uptime()}s. Batt: {get_battery().get('percentage')}%", 
             title="Heartbeat", tags=["robot", "heart"])
        time.sleep(3600)

def run_server():
    server = HTTPServer(('0.0.0.0', PORT), BridgeHandler)
    log.info(f"Bridge V6 started on port {PORT}")
    ntfy(f"Bridge v{VERSION} online", title="Bridge Status", tags=["rocket", "check"])
    threading.Thread(target=heartbeat_loop, daemon=True).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()

if __name__ == "__main__":
    run_server()
