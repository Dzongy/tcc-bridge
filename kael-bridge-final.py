#!/usr/bin/env python3
import os, json, time, threading, subprocess, logging, socket, sys, traceback, signal
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
from urllib.parse import urlparse, parse_qs

# --- CONFIG ---
CONFIG = {
    "PORT":          int(os.environ.get("PORT", 8080)),
    "AUTH_TOKEN":    os.environ.get("AUTH_TOKEN", "amos-bridge-2026"),
    "NTFY_TOPIC":    os.environ.get("NTFY_TOPIC", "zenith-escape"),
    "DEVICE_ID":     os.environ.get("DEVICE_ID", socket.gethostname()),
    "VERSION":       "2.0.0-bulletproof",
    "LOG_FILE":      os.path.expanduser("~/tcc-bridge.log"),
}

# --- LOGGING ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", handlers=[logging.FileHandler(CONFIG["LOG_FILE"]), logging.StreamHandler()])
logger = logging.getLogger("BridgeV2")

def ntfy(msg, priority=3, tags=None):
    try:
        url = f"https://ntfy.sh/{CONFIG['NTFY_TOPIC']}"
        headers = {"Priority": str(priority)}
        if tags: headers["Tags"] = ",".join(tags)
        req = Request(url, data=msg.encode(), headers=headers, method="POST")
        urlopen(req, timeout=5)
    except Exception as e: logger.error(f"ntfy failed: {e}")

class BridgeHandler(BaseHTTPRequestHandler):
    def check_auth(self):
        auth_header = self.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            if auth_header[7:] == CONFIG["AUTH_TOKEN"]: return True
        query = parse_qs(urlparse(self.path).query)
        if query.get("auth", [None])[0] == CONFIG["AUTH_TOKEN"]: return True
        return False

    def send_resp(self, code, data):
        self.send_response(code); self.send_header("Content-Type", "application/json"); self.end_headers(); self.wfile.write(json.dumps(data).encode())

    def do_GET(self):
        parsed_path = urlparse(self.path); path = parsed_path.path; query = parse_qs(parsed_path.query)
        if path == "/health": return self.send_resp(200, {"status": "ok", "version": CONFIG["VERSION"]})
        if not self.check_auth(): return self.send_resp(401, {"error": "Unauthorized"})
        if path == "/status": return self.send_resp(200, {"status": "online", "device": CONFIG["DEVICE_ID"], "uptime": time.time() - START_TIME})
        if path == "/toast": subprocess.run(["termux-toast", query.get("msg", ["Bridge Hello"])[0]]); return self.send_resp(200, {"status": "ok"})
        self.send_resp(404, {"error": "Not Found"})

    def do_POST(self):
        if not self.check_auth(): return self.send_resp(401, {"error": "Unauthorized"})
        content_length = int(self.headers.get('Content-Length', 0))
        try: body = json.loads(self.rfile.read(content_length).decode()) if content_length > 0 else {}
        except: return self.send_resp(400, {"error": "Invalid JSON"})
        path = urlparse(self.path).path
        if path == "/exec":
            cmd = body.get("cmd"); 
            if not cmd: return self.send_resp(400, {"error": "Missing cmd"})
            try: res = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT).decode(); return self.send_resp(200, {"output": res})
            except subprocess.CalledProcessError as e: return self.send_resp(500, {"error": e.output.decode()})
        if path == "/speak": subprocess.run(["termux-tts-speak", body.get("msg", "Bridge voice active")]); return self.send_resp(200, {"status": "ok"})
        self.send_resp(404, {"error": "Not Found"})

START_TIME = time.time()
if __name__ == "__main__":
    try:
        server = HTTPServer(('0.0.0.0', CONFIG["PORT"]), BridgeHandler)
        ntfy(f"🚀 Bridge V2 Online: {CONFIG['DEVICE_ID']} on {CONFIG['PORT']}", tags=["rocket"])
        server.serve_forever()
    except Exception as e:
        ntfy(f"⚠️ Bridge Crash: {e}", priority=5, tags=["warning"]); sys.exit(1)
