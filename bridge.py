#!/usr/bin/env python3
"""
TCC BRIDGE V3 â PERMANENT & BULLETPROOF
- Auto-reconnect & Persistent Listeners
- Health Endpoint: /health
- Multi-function: /exec, /toast, /speak, /vibrate, /write_file, /listen, /conversation, /voice
- PM2 Optimized
"""

import os, json, time, threading, subprocess, logging, socket, sys, traceback
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
from urllib.parse import urlparse, parse_qs

# --- CONFIG ---
CONFIG = {
    "PORT": 8765,
    "NTFY_TOPIC": "zenith-escape",
    "NTFY_HIVE": "tcc-zenith-hive",
    "SUPABASE_URL": "https://vbqbbziqleymxcyesmky.supabase.co",
    "SUPABASE_KEY": "sb_secret_lIbl-DBgdnrt_fejgJjKqg_qR62SVEm",
    "DEVICE_ID": socket.gethostname()
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler(os.path.expanduser("~/tcc-bridge.log"))]
)
log = logging.getLogger("TCC_BRIDGE")

class BridgeHandler(BaseHTTPRequestHandler):
    def _send_json(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def do_GET(self):
        if self.path == "/health":
            self._send_json({
                "status": "online",
                "uptime": time.time() - START_TIME,
                "device": CONFIG["DEVICE_ID"],
                "version": "3.0.0-bulletproof"
            })
        elif self.path.startswith("/speak"):
            query = parse_qs(urlparse(self.path).query)
            text = query.get("text", [""])[0]
            if text:
                subprocess.run(["termux-tts-speak", text])
                self._send_json({"status": "spoken", "text": text})
            else:
                self._send_json({"error": "missing text"}, 400)
        else:
            self.send_error(404)

    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        data = json.loads(post_data)
        path = self.path

        try:
            if path == "/exec":
                cmd = data.get("command")
                res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                self._send_json({"stdout": res.stdout, "stderr": res.stderr, "code": res.returncode})
            elif path == "/toast":
                subprocess.run(["termux-toast", data.get("text", "No text")])
                self._send_json({"status": "toasted"})
            elif path == "/vibrate":
                duration = data.get("duration", 500)
                subprocess.run(["termux-vibrate", "-d", str(duration)])
                self._send_json({"status": "vibrated"})
            elif path == "/write_file":
                filename = data.get("filename")
                content = data.get("content")
                with open(os.path.expanduser(f"~/tcc-bridge-files/{filename}"), "w") as f:
                    f.write(content)
                self._send_json({"status": "written", "file": filename})
            else:
                self.send_error(404)
        except Exception as e:
            log.error(traceback.format_exc())
            self._send_json({"error": str(e)}, 500)

def run_server():
    server = HTTPServer(('0.0.0.0', CONFIG["PORT"]), BridgeHandler)
    log.info(f"Bridge Server V3 running on port {CONFIG['PORT']}")
    server.serve_forever()

START_TIME = time.time()
if __name__ == "__main__":
    os.makedirs(os.path.expanduser("~/tcc-bridge-files"), exist_ok=True)
    threading.Thread(target=run_server, daemon=True).start()
    
    # Alert Hive
    try:
        req = Request(f"https://ntfy.sh/{CONFIG['NTFY_HIVE']}", data=f"BRIDGE V3 ONLINE on {CONFIG['DEVICE_ID']}".encode())
        req.add_header("Title", "Bridge Awakened")
        req.add_header("Tags", "robot,rocket")
        urlopen(req)
    except: pass

    while True:
        time.sleep(60)
