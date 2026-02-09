#!/usr/bin/env python3
"""AMOS Bridge v2 - Phone Control HTTP Server
Runs on Termux, exposes endpoints for remote control.
Endpoints: /exec, /toast, /speak, /vibrate, /write_file, /health
Auth: X-Auth header token
"""
import subprocess
import json
import os
import sys
import base64
import socket
import signal
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler

AUTH_TOKEN = "amos-bridge-2026"
PORT = 8080
LOG_FILE = os.path.expanduser("~/bridge.log")

# --- Logging setup (file + stderr, unbuffered) ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stderr),
    ],
)
log = logging.getLogger("bridge")


def kill_port(port):
    """Kill any process holding the port. Works without root on Termux."""
    try:
        r = subprocess.run(
            f"lsof -ti:{port}", shell=True, capture_output=True, text=True
        )
        pids = r.stdout.strip().split()
        for pid in pids:
            if pid:
                os.kill(int(pid), signal.SIGTERM)
                log.info("Killed stale process %s on port %d", pid, port)
    except Exception:
        pass  # lsof may not exist; we handle bind failure below


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
            self._respond(200, {"status": "ok", "version": "2.1"})
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

        routes = {
            "/exec": self._handle_exec,
            "/toast": self._handle_toast,
            "/speak": self._handle_speak,
            "/vibrate": self._handle_vibrate,
            "/write_file": self._handle_write_file,
        }
        handler = routes.get(self.path)
        if handler:
            handler(body)
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

    def log_message(self, fmt, *args):
        log.info("%s %s", self.client_address[0], fmt % args)


if __name__ == "__main__":
    try:
        # Kill anything squatting on our port
        kill_port(PORT)

        # SO_REUSEADDR: let the OS rebind immediately
        class ReusableHTTPServer(HTTPServer):
            allow_reuse_address = True
            # Also allow reuse on Linux/Termux
            def server_bind(self):
                self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                super().server_bind()

        server = ReusableHTTPServer(("0.0.0.0", PORT), BridgeHandler)
        log.info("AMOS Bridge v2.1 listening on 0.0.0.0:%d", PORT)
        print(f"AMOS Bridge v2.1 listening on 0.0.0.0:{PORT}", flush=True)
        server.serve_forever()

    except OSError as e:
        log.error("FATAL: Cannot bind port %d -- %s", PORT, e)
        print(f"FATAL: Cannot bind port {PORT} -- {e}", file=sys.stderr, flush=True)
        sys.exit(1)

    except KeyboardInterrupt:
        log.info("Bridge shutting down.")
        print("Bridge shutting down.", flush=True)
        server.server_close()

    except Exception as e:
        log.error("FATAL: Unexpected error -- %s", e, exc_info=True)
        print(f"FATAL: {e}", file=sys.stderr, flush=True)
        sys.exit(1)
