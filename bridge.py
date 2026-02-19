#!/usr/bin/env python3
"""
TCC Bridge v5.1.0 â BULLETPROOF EDITION (KAEL MOD)
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
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://vbqbbziqleymxcyesmky.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")
NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "tcc-zenith-hive")
PUBLIC_URL = "https://zenith.cosmic-claw.com"
VERSION = "5.1.0"
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

def tunnel_check_loop():
    """Periodically verifies if the public tunnel is actually working."""
    while True:
        time.sleep(600) # Check every 10 mins
        try:
            req = Request(f"{PUBLIC_URL}/health")
            with urlopen(req, timeout=10) as response:
                if response.status != 200:
                    raise Exception(f"Status {response.status}")
            log.info("Public tunnel health check: OK")
        except Exception as e:
            log.error(f"Public tunnel health check: FAILED - {e}")
            ntfy(f"Tunnel {PUBLIC_URL} is unreachable from outside, but bridge is running locally. Check cloudflared.", 
                 "Tunnel Down", 5, ["warning", "cloud"])

class TCCBridgeHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/health":
            self.send_response(200)
            self.end_headers()
            uptime = int(time.time() - START_TIME)
            self.wfile.write(json.dumps({"status": "alive", "version": VERSION, "uptime_sec": uptime}).encode())
            return
        
        # Auth check for other endpoints
        token = self.headers.get("X-Auth")
        if token != AUTH_TOKEN:
            self.send_response(401)
            self.end_headers()
            return

        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)

        if parsed.path == "/toast":
            msg = params.get("text", ["Hello"])[0]
            subprocess.run(f"termux-toast '{msg}'", shell=True)
            self._send_ok("Toast sent")
        elif parsed.path == "/speak":
            msg = params.get("text", ["Hello"])[0]
            subprocess.run(f"termux-tts-speak '{msg}'", shell=True)
            self._send_ok("Speaking")
        elif parsed.path == "/vibrate":
            ms = params.get("ms", ["500"])[0]
            subprocess.run(f"termux-vibrate -d {ms}", shell=True)
            self._send_ok("Vibrating")
        else:
            self.send_response(404)
            self.end_headers()

    def _send_ok(self, msg):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(json.dumps({"status": "ok", "message": msg}).encode())

def run_server():
    server = HTTPServer(("0.0.0.0", PORT), TCCBridgeHandler)
    log.info(f"Bridge v{VERSION} starting on port {PORT}...")
    ntfy(f"Bridge v{VERSION} is online and armed.", "Bridge Started", 3, ["robot", "check"])
    
    # Start tunnel monitor
    threading.Thread(target=tunnel_check_loop, daemon=True).start()
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()

if __name__ == "__main__":
    run_server()
