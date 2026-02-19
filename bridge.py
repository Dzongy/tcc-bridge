#!/usr/bin/env python3
"""
TCC Bridge v5.2 — BULLETPROOF EDITION
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
HEALTH_INTERVAL = 300
PUBLIC_URL = os.environ.get("PUBLIC_URL", "https://zenith.cosmic-claw.com")
VERSION = "5.2.0"
START_TIME = time.time()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler(sys.stderr)])
log = logging.getLogger("bridge")

def ntfy(msg, priority=3):
    try:
        req = Request(f"https://ntfy.sh/{NTFY_TOPIC}", data=msg.encode('utf-8'))
        req.add_header("Title", "Bridge V2 Alert")
        req.add_header("Priority", str(priority))
        urlopen(req)
    except Exception as e: log.error(f"ntfy failed: {e}")

class HealthThread(threading.Thread):
    def run(self):
        log.info("Health monitoring started.")
        while True:
            time.sleep(HEALTH_INTERVAL)
            try:
                # 1. Check local health
                uptime = int(time.time() - START_TIME)
                state = {"status": "online", "uptime": uptime, "version": VERSION, "timestamp": time.time()}
                
                # 2. Push to Supabase (Mocked for now, need exact table)
                # ...
                
                # 3. Check Public URL (Self-reachability)
                try:
                    urlopen(f"{PUBLIC_URL}/health", timeout=15)
                    log.info("Public health check passed.")
                except Exception as e:
                    log.warning(f"Public health check FAILED: {e}")
                    ntfy(f"⚠️ Bridge unreachable from outside! Attempting tunnel restart. Error: {e}", 4)
                    subprocess.run("pm2 restart cloudflared", shell=True)
            except Exception as e: log.error(f"HealthThread error: {e}")

class BridgeHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/health":
            self.send_response(200); self.end_headers()
            self.wfile.write(json.dumps({"status": "ok", "version": VERSION}).encode())
        else:
            self.send_response(404); self.end_headers()

def run_server():
    server = HTTPServer(('0.0.0.0', PORT), BridgeHandler)
    log.info(f"Bridge V2 listening on {PORT}...")
    t = HealthThread(daemon=True)
    t.start()
    server.serve_forever()

if __name__ == "__main__":
    run_server()
