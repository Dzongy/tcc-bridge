#!/usr/bin/env python3
"""AMOS Bridge v2 - Phone Control HTTP Server
Runs on Termux, exposes endpoints for remote control.
Endpoints: /exec, /toast, /speak, /vibrate, /write_file, /health
Auth: X-Auth header token
"""
import subprocess
import json
import os
import base64
from http.server import HTTPServer, BaseHTTPRequestHandler

AUTH_TOKEN = "amos-bridge-2026"
PORT = 8080

class BridgeHandler(BaseHTTPRequestHandler):
    def _auth(self):
        token = self.headers.get("X-Auth", "")
        if token != AUTH_TOKEN:
            self._respond(401, {"error": "unauthorized"})
            return False
        return True

    def _respond(self, code, data):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def _read_body(self):
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return {}
        return json.loads(self.rfile.read(length))

    def do_GET(self):
        if self.path == "/health":
            self._respond(200, {"status": "ok", "version": "2.0"})
            return
        self._respond(404, {"error": "not found"})

    def do_POST(self):
        if not self._auth():
            return
        try:
            body = self._read_body()
        except Exception as e:
            self._respond(400, {"error": f"bad request: {e}"})
            return

        if self.path == "/exec":
            self._handle_exec(body)
        elif self.path == "/toast":
            self._handle_toast(body)
        elif self.path == "/speak":
            self._handle_speak(body)
        elif self.path == "/vibrate":
            self._handle_vibrate(body)
        elif self.path == "/write_file":
            self._handle_write_file(body)
        else:
            self._respond(404, {"error": "not found"})

    def _run(self, cmd, timeout=30):
        try:
            r = subprocess.run(
                cmd, shell=True, capture_output=True, text=True, timeout=timeout
            )
            return r.returncode, r.stdout.strip(), r.stderr.strip()
        except subprocess.TimeoutExpired:
            return -1, "", "timeout"
        except Exception as e:
            return -1, "", str(e)

    def _handle_exec(self, body):
        cmd = body.get("cmd", "")
        if not cmd:
            self._respond(400, {"error": "missing cmd"})
            return
        timeout = body.get("timeout", 30)
        code, stdout, stderr = self._run(cmd, timeout=timeout)
        self._respond(200, {"returncode": code, "stdout": stdout, "stderr": stderr})

    def _handle_toast(self, body):
        text = body.get("text", "AMOS")
        code, stdout, stderr = self._run(f'termux-toast "{text}"')
        self._respond(200, {"ok": code == 0, "stderr": stderr})

    def _handle_speak(self, body):
        text = body.get("text", "")
        if not text:
            self._respond(400, {"error": "missing text"})
            return
        code, stdout, stderr = self._run(f'termux-tts-speak "{text}"')
        self._respond(200, {"ok": code == 0, "stderr": stderr})

    def _handle_vibrate(self, body):
        ms = body.get("ms", 500)
        code, stdout, stderr = self._run(f"termux-vibrate -d {ms}")
        self._respond(200, {"ok": code == 0, "stderr": stderr})

    def _handle_write_file(self, body):
        path = body.get("path", "")
        content = body.get("content", "")
        b64 = body.get("base64", False)
        if not path:
            self._respond(400, {"error": "missing path"})
            return
        try:
            os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
            if b64:
                data = base64.b64decode(content)
                with open(path, "wb") as f:
                    f.write(data)
            else:
                with open(path, "w") as f:
                    f.write(content)
            self._respond(200, {"ok": True, "path": path})
        except Exception as e:
            self._respond(500, {"error": str(e)})

    def log_message(self, format, *args):
        pass

if __name__ == "__main__":
    print(f"AMOS Bridge v2 starting on port {PORT}...")
    server = HTTPServer(("0.0.0.0", PORT), BridgeHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Bridge shutting down.")
        server.server_close()
