#!/usr/bin/env python3
"""
TCC Bridge V6.1.1 - THE BULLETPROOF EDITION (KAEL MERGE)
Built by KAEL God Builder for Commander.
Merged Lineage: Xena v2.2 + Kael v5.3.0 + V2 Evolved + V6 Robustness.
"""
import os, sys, json, time, signal, logging, subprocess, threading, socket, traceback
from datetime import datetime, timezone
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
from urllib.parse import urlparse, parse_qs

# --- CONFIG ---
AUTH_TOKEN   = os.environ.get("BRIDGE_AUTH", "amos-bridge-2026")
PORT         = int(os.environ.get("BRIDGE_PORT", "8765"))
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://vbqbbziqleymxcyesmky.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")
NTFY_TOPIC   = os.environ.get("NTFY_TOPIC", "tcc-zenith-hive")
PUBLIC_URL   = os.environ.get("PUBLIC_URL", "https://zenith.cosmic-claw.com")
DEVICE_ID    = "amos-arms"
LOG_FILE     = os.path.expanduser("~/bridge.log")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler(sys.stderr)]
)
log = logging.getLogger("bridge")

def ntfy(msg, title="Bridge V6", priority=3, tags=None):
    try:
        url = f"https://ntfy.sh/{NTFY_TOPIC}"
        headers = {"Title": title, "Priority": str(priority)}
        if tags: headers["Tags"] = ",".join(tags)
        req = Request(url, data=msg.encode(), headers=headers)
        urlopen(req, timeout=5)
    except: pass

def push_state():
    if not SUPABASE_KEY: return
    try:
        payload = {
            "device_id": DEVICE_ID,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "bridge_online": True,
            "tunnel_online": True
        }
        req = Request(f"{SUPABASE_URL}/rest/v1/device_state", 
                      data=json.dumps(payload).encode(),
                      headers={
                          "apikey": SUPABASE_KEY,
                          "Authorization": f"Bearer {SUPABASE_KEY}",
                          "Content-Type": "application/json",
                          "Prefer": "resolution=merge-duplicates"
                      }, method="POST")
        urlopen(req, timeout=10)
    except Exception as e:
        log.error(f"State push failed: {e}")

class BridgeHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/health":
            self.send_response(200); self.end_headers(); self.wfile.write(b"OK")
            return
        self.send_error(404)

    def do_POST(self):
        auth = self.headers.get("Authorization", "")
        if auth != f"Bearer {AUTH_TOKEN}":
            self.send_error(401); return
            
        content_len = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_len)
        try: data = json.loads(post_data)
        except: data = {}

        if self.path == "/exec":
            cmd = data.get("cmd", "")
            res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            self.send_response(200); self.end_headers()
            self.wfile.write(json.dumps({"stdout": res.stdout, "stderr": res.stderr}).encode())
        elif self.path == "/toast":
            msg = data.get("msg", "Bridge V6")
            subprocess.run(f"termux-toast '{msg}'", shell=True)
            self.send_response(200); self.end_headers(); self.wfile.write(b"OK")
        else:
            self.send_error(404)

def reporter():
    while True:
        try: push_state()
        except: pass
        time.sleep(300)

if __name__ == "__main__":
    log.info(f"Starting TCC Bridge V6.1.1 on port {PORT}...")
    threading.Thread(target=reporter, daemon=True).start()
    server = HTTPServer(("0.0.0.0", PORT), BridgeHandler)
    server.serve_forever()
