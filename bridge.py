#!/usr/bin/env python3
"""
TCC Bridge v7.2 - MINIMAL RECOVERY EDITION
Brain #10 - Kael - Guaranteed Startup
Only stdlib. No threads. No Supabase. Just works.
"""

import subprocess
import json
import os
import time
import socket
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

VERSION = "7.2-minimal"
PORT = int(os.environ.get("BRIDGE_PORT", "8765"))
AUTH_TOKEN = os.environ.get("BRIDGE_AUTH", "amos-bridge-2026")
DEVICE_ID = os.environ.get("DEVICE_ID", socket.gethostname())
START_TIME = time.time()

def check_auth(headers, params):
    """Check auth from header or query param."""
    auth = headers.get("X-Auth", "") or headers.get("Authorization", "")
    if auth.replace("Bearer ", "") == AUTH_TOKEN:
        return True
    if params.get("auth", [""])[0] == AUTH_TOKEN:
        return True
    return False

def get_battery():
    try:
        r = subprocess.run(["termux-battery-status"], capture_output=True, text=True, timeout=5)
        d = json.loads(r.stdout)
        return d.get("percentage", -1)
    except Exception:
        return -1

class BridgeHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass  # Suppress default logging

    def _send_json(self, data, code=200):
        body = json.dumps(data).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _parse_params(self):
        parsed = urlparse(self.path)
        return parsed.path, parse_qs(parsed.query)

    def _read_body(self):
        length = int(self.headers.get("Content-Length", 0))
        if length > 0:
            return json.loads(self.rfile.read(length))
        return {}

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Auth, Authorization")
        self.end_headers()

    def do_GET(self):
        path, params = self._parse_params()

        if path == "/health":
            self._send_json({"status": "ok", "version": VERSION, "uptime": int(time.time() - START_TIME)})
            return

        if path == "/state":
            self._send_json({
                "device_id": DEVICE_ID,
                "version": VERSION,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "battery": get_battery(),
                "uptime_sys": subprocess.getoutput("uptime -p") or "unknown",
                "bridge_uptime": int(time.time() - START_TIME),
                "status": "online"
            })
            return

        if not check_auth(self.headers, params):
            self._send_json({"error": "unauthorized"}, 401)
            return

        if path == "/exec":
            cmd = params.get("cmd", [""])[0]
            if not cmd:
                self._send_json({"error": "missing cmd parameter"}, 400)
                return
            try:
                r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
                self._send_json({"stdout": r.stdout, "stderr": r.stderr, "code": r.returncode})
            except subprocess.TimeoutExpired:
                self._send_json({"error": "timeout"}, 408)
            return

        if path == "/toast":
            msg = params.get("msg", params.get("text", ["Kael says hi"]))[0]
            subprocess.Popen(["termux-toast", msg])
            self._send_json({"ok": True, "message": msg})
            return

        if path == "/speak":
            msg = params.get("msg", params.get("text", ["Hello Commander"]))[0]
            subprocess.Popen(["termux-tts-speak", msg])
            self._send_json({"ok": True, "message": msg})
            return

        if path == "/vibrate":
            dur = params.get("duration", ["500"])[0]
            subprocess.Popen(["termux-vibrate", "-d", dur])
            self._send_json({"ok": True, "duration": dur})
            return

        self._send_json({"error": "not_found"}, 404)

    def do_POST(self):
        path, params = self._parse_params()

        if path == "/health":
            self._send_json({"status": "ok", "version": VERSION, "uptime": int(time.time() - START_TIME)})
            return

        if not check_auth(self.headers, params):
            self._send_json({"error": "unauthorized"}, 401)
            return

        try:
            body = self._read_body()
        except Exception:
            body = {}

        if path == "/exec":
            cmd = body.get("cmd", body.get("command", ""))
            if not cmd:
                self._send_json({"error": "missing cmd/command"}, 400)
                return
            try:
                r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
                self._send_json({"stdout": r.stdout, "stderr": r.stderr, "code": r.returncode})
            except subprocess.TimeoutExpired:
                self._send_json({"error": "timeout"}, 408)
            return

        if path == "/toast":
            msg = body.get("msg", body.get("text", body.get("message", "Kael says hi")))
            subprocess.Popen(["termux-toast", str(msg)])
            self._send_json({"ok": True, "message": msg})
            return

        if path == "/speak":
            msg = body.get("msg", body.get("text", body.get("message", "Hello Commander")))
            subprocess.Popen(["termux-tts-speak", str(msg)])
            self._send_json({"ok": True, "message": msg})
            return

        if path == "/vibrate":
            dur = str(body.get("duration", 500))
            subprocess.Popen(["termux-vibrate", "-d", dur])
            self._send_json({"ok": True, "duration": dur})
            return

        if path == "/notify":
            # ntfy push
            msg = body.get("message", body.get("msg", ""))
            topic = body.get("topic", "tcc-zenith-hive")
            try:
                from urllib.request import Request, urlopen
                req = Request(f"https://ntfy.sh/{topic}", data=msg.encode())
                req.add_header("Title", body.get("title", "Bridge Notification"))
                urlopen(req, timeout=5)
                self._send_json({"ok": True})
            except Exception as e:
                self._send_json({"error": str(e)}, 500)
            return

        self._send_json({"error": "not_found"}, 404)

if __name__ == "__main__":
    print(f"TCC Bridge v{VERSION} starting on 0.0.0.0:{PORT}")
    print(f"  AUTH: {AUTH_TOKEN}")
    print(f"  DEVICE: {DEVICE_ID}")
    server = HTTPServer(("0.0.0.0", PORT), BridgeHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Bridge stopped.")
        server.server_close()
