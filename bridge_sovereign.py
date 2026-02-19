#!/usr/bin/env python3
"""
TCC Bridge v5.1.0 — BULLETPROOF EDITION
Permanent phone control HTTP server for Termux.
"""
import subprocess, json, os, sys, base64, socket, signal, logging, time, threading, traceback
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.request import Request, urlopen
from urllib.error import URLError
from urllib.parse import parse_qs, urlparse

# --- Config ---
AUTH_TOKEN = os.environ.get("BRIDGE_AUTH", "amos-bridge-2026")
PORT = int(os.environ.get("BRIDGE_PORT", "8080"))
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://vbqbbziqleymxcyesmky.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")
NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "tcc-zenith-hive")
HEARTBEAT_INTERVAL = 300
VERSION = "5.1.0"

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(os.path.expanduser("~/bridge.log")),
        logging.StreamHandler()
    ]
)

class BridgeHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args): return # Silence default logs
    
    def do_GET(self):
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            health_data = {
                "status": "alive",
                "version": VERSION,
                "uptime": time.time() - START_TIME,
                "device": socket.gethostname()
            }
            self.wfile.write(json.dumps(health_data).encode())
            return
        self.send_error(404)

    def do_POST(self):
        auth = self.headers.get('X-Auth')
        if auth != AUTH_TOKEN:
            logging.warning(f"Unauthorized access attempt from {self.client_address}")
            self.send_response(403)
            self.end_headers()
            return

        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode('utf-8') if content_length > 0 else "{}"
        
        try:
            data = json.loads(body)
        except:
            data = {}
            
        path = self.path
        res = {"success": False, "output": ""}
        
        try:
            if path == '/exec':
                cmd = data.get('command')
                logging.info(f"Executing: {cmd}")
                r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60)
                res = {"success": r.returncode == 0, "output": r.stdout + r.stderr, "code": r.returncode}
            elif path == '/toast':
                msg = data.get('message', '')
                subprocess.run(f"termux-toast '{msg}'", shell=True)
                res = {"success": True}
            elif path == '/vibrate':
                ms = data.get('ms', 500)
                subprocess.run(f"termux-vibrate -d {ms}", shell=True)
                res = {"success": True}
            elif path == '/speak':
                text = data.get('text', '')
                subprocess.run(f"termux-tts-speak '{text}'", shell=True)
                res = {"success": True}
            elif path == '/write_file':
                file_path = data.get('path')
                content = data.get('content', '')
                with open(os.path.expanduser(file_path), 'w') as f:
                    f.write(content)
                res = {"success": True}
        except Exception as e:
            logging.error(f"Error handling {path}: {str(e)}")
            res = {"success": False, "error": str(e), "trace": traceback.format_exc()}

        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(res).encode())

def push_heartbeat():
    logging.info("Heartbeat thread started")
    while True:
        try:
            # Simple ping to ntfy to show we're alive
            payload = f"Bridge v{VERSION} Active | Uptime: {int(time.time() - START_TIME)}s".encode()
            req = Request(f"https://ntfy.sh/{NTFY_TOPIC}", data=payload, method='POST')
            urlopen(req, timeout=10)
        except Exception as e:
            logging.error(f"Heartbeat failed: {e}")
        time.sleep(HEARTBEAT_INTERVAL)

START_TIME = time.time()

def run():
    # Set up signal handlers for graceful exit
    def handler(signum, frame):
        logging.info("Bridge shutting down...")
        sys.exit(0)
    signal.signal(signal.SIGINT, handler)
    signal.signal(signal.SIGTERM, handler)

    # Start heartbeat
    threading.Thread(target=push_heartbeat, daemon=True).start()

    # Start server
    server = HTTPServer(('0.0.0.0', PORT), BridgeHandler)
    logging.info(f"Bridge v{VERSION} BULLETPROOF starting on port {PORT}")
    server.serve_forever()

if __name__ == "__main__":
    run()
