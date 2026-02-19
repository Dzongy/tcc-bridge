#!/usr/bin/env python3
"""
TCC Bridge v6.0 — BULLETPROOF EDITION
Built by KAEL for Commander.
Role: Persistent Bridge between Twin/Kael and Android/Termux.
Features: Auto-reconnect, Health endpoint, State push to Supabase, PM2 ready.
"""

import os, json, time, threading, subprocess, logging, traceback, socket, sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
from urllib.parse import urlparse, parse_qs
from datetime import datetime, timezone

# --- CONFIG ---
SUPABASE_URL  = "https://vbqbbziqleymxcyesmky.supabase.co"
SUPABASE_KEY  = "sb_secret_lIbl-DBgdnrt_fejgJjKqg_qR62SVEm"
NTFY_TOPIC    = "tcc-zenith-hive"
PORT          = 8765
REPORT_SEC    = 60
DEVICE_ID     = "amos-arms" # socket.gethostname() often returns 'localhost' in Termux

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("BridgeV6")

class BridgeHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args): return # Silence standard logs

    def send_json(self, data, status=200):
        self.send_response(status)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def do_GET(self):
        path = urlparse(self.path).path
        if path == '/health':
            self.send_json({"status": "ok", "device": DEVICE_ID, "time": time.time()})
        elif path == '/log':
            # Returns last 50 lines of pm2 log if possible
            try:
                log = subprocess.check_output("tail -n 50 ~/.pm2/logs/bridge-out.log", shell=True).decode()
                self.send_json({"log": log})
            except:
                self.send_json({"error": "Could not read logs"}, 500)
        else:
            self.send_json({"error": "Not Found"}, 404)

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode()
        data = json.loads(body) if body else {}
        path = urlparse(self.path).path

        try:
            if path == '/exec':
                cmd = data.get('cmd')
                res = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT).decode()
                self.send_json({"output": res})
            elif path == '/toast':
                msg = data.get('msg', 'Hello from Bridge')
                subprocess.run(f"termux-toast '{msg}'", shell=True)
                self.send_json({"status": "sent"})
            elif path == '/vibrate':
                subprocess.run("termux-vibrate", shell=True)
                self.send_json({"status": "vibrated"})
            elif path == '/speak':
                msg = data.get('msg', 'Bridge online')
                subprocess.run(f"termux-tts-speak '{msg}'", shell=True)
                self.send_json({"status": "speaking"})
            else:
                self.send_json({"error": "Unknown endpoint"}, 404)
        except Exception as e:
            logger.error(traceback.format_exc())
            self.send_json({"error": str(e)}, 500)

def push_state_loop():
    logger.info("Starting State Push Loop")
    while True:
        try:
            # Get Device Info
            battery = json.loads(subprocess.check_output("termux-battery-status", shell=True))
            # Push to Supabase device_state
            state = {
                "device_id": DEVICE_ID,
                "battery": battery.get('percentage', 0),
                "hostname": socket.gethostname(),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            req = Request(f"{SUPABASE_URL}/rest/v1/device_state", 
                          data=json.dumps(state).encode(),
                          headers={
                              "apikey": SUPABASE_KEY, 
                              "Authorization": f"Bearer {SUPABASE_KEY}", 
                              "Content-Type": "application/json", 
                              "Prefer": "resolution=merge-duplicates"
                          })
            urlopen(req)
            logger.info("State pushed to Supabase")
        except Exception as e:
            logger.error(f"Supabase push failed: {e}")
        time.sleep(REPORT_SEC)

def run_server():
    server = HTTPServer(('0.0.0.0', PORT), BridgeHandler)
    logger.info(f"Bridge V6 listening on port {PORT}")
    server.serve_forever()

if __name__ == "__main__":
    # Notify ntfy
    try:
        urlopen(Request(f"https://ntfy.sh/{NTFY_TOPIC}", data=f"Bridge V6 starting on {DEVICE_ID}".encode()))
    except: pass

    threading.Thread(target=push_state_loop, daemon=True).start()
    run_server()
