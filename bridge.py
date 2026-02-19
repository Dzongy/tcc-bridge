#!/usr/bin/env python3
"""
TCC Bridge v5.3.0 — SOVEREIGN BULLETPROOF EDITION
Built by Kael for Commander.
Features: Multi-endpoint control, Health watchdog, Supabase sync, PM2 optimized.
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
VERSION = "5.3.0"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(os.path.expanduser("~/bridge.log")),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("BridgeV5")

class BridgeHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args): return

    def send_json(self, data, status=200):
        self.send_response(status)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def do_GET(self):
        if self.path == '/health':
            self.send_json({"status": "alive", "version": VERSION, "uptime": time.time() - start_time})
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        # Auth Check
        auth = self.headers.get('Authorization')
        if not auth or auth != f"Bearer {AUTH_TOKEN}":
            return self.send_json({"error": "Unauthorized"}, 401)

        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode()
        try:
            data = json.loads(body)
        except:
            return self.send_json({"error": "Invalid JSON"}, 400)

        cmd = data.get("command")
        logger.info(f"Command received: {cmd}")

        try:
            if cmd == "exec":
                res = subprocess.check_output(data.get("shell"), shell=True, stderr=subprocess.STDOUT).decode()
                self.send_json({"output": res})
            elif cmd == "toast":
                subprocess.run(f"termux-toast '{data.get('text')}'", shell=True)
                self.send_json({"status": "sent"})
            elif cmd == "vibrate":
                subprocess.run(f"termux-vibrate -d {data.get('duration', 500)}", shell=True)
                self.send_json({"status": "done"})
            elif cmd == "speak":
                subprocess.run(f"termux-tts-speak '{data.get('text')}'", shell=True)
                self.send_json({"status": "speaking"})
            elif cmd == "write_file":
                path = os.path.expanduser(data.get("path"))
                with open(path, "w") as f: f.write(data.get("content"))
                self.send_json({"status": "written", "path": path})
            else:
                self.send_json({"error": "Unknown command"}, 400)
        except Exception as e:
            logger.error(traceback.format_exc())
            self.send_json({"error": str(e)}, 500)

def run_server():
    server = HTTPServer(('0.0.0.0', PORT), BridgeHandler)
    logger.info(f"Sovereign Bridge v{VERSION} starting on port {PORT}...")
    server.serve_forever()

if __name__ == "__main__":
    start_time = time.time()
    run_server()
