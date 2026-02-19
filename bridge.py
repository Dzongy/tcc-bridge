#!/usr/bin/env python3
"""
BRIDGE V2 — BULLETPROOF EDITION
bridge.py v5.2.0
Kael God Builder
"""

import json
import logging
import os
import subprocess
import sys
import threading
import time
import traceback
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

# ──────────────────────────────────────────
# LOGGING
# ──────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(os.path.expanduser("~/bridge.log"), encoding="utf-8"),
    ],
)
log = logging.getLogger("bridge")

# ──────────────────────────────────────────
# CONFIG
# ──────────────────────────────────────────
VERSION = "5.2.0"
BASE_PORT = int(os.environ.get("BRIDGE_PORT", 8765))
PUBLIC_URL = os.environ.get("BRIDGE_PUBLIC_URL", "https://zenith.cosmic-claw.com/health")
NTFY_URL = os.environ.get("NTFY_URL", "https://ntfy.sh/tcc-zenith-hive")
TUNNEL_CHECK_INTERVAL = int(os.environ.get("TUNNEL_CHECK_INTERVAL", 120))  # seconds
TUNNEL_FAIL_THRESHOLD = int(os.environ.get("TUNNEL_FAIL_THRESHOLD", 3))

START_TIME = time.time()


# ──────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────

def get_uptime() -> float:
    return round(time.time() - START_TIME, 2)


def get_battery() -> dict:
    """Returns battery percentage and charging status via termux-battery-status."""
    try:
        result = subprocess.run(
            ["termux-battery-status"],
            capture_output=True, text=True, timeout=8
        )
        data = json.loads(result.stdout)
        return {
            "percentage": data.get("percentage", -1),
            "plugged": data.get("plugged", "UNKNOWN"),
            "status": data.get("status", "UNKNOWN"),
        }
    except Exception as e:
        log.warning("get_battery failed: %s", e)
        return {"percentage": -1, "plugged": "UNKNOWN", "status": "UNKNOWN"}


def send_ntfy(title: str, message: str, priority: str = "high", tags: str = "warning") -> bool:
    """Send a notification via ntfy."""
    try:
        req = Request(
            NTFY_URL,
            data=message.encode("utf-8"),
            headers={
                "Title": title,
                "Priority": priority,
                "Tags": tags,
            },
            method="POST",
        )
        with urlopen(req, timeout=10) as resp:
            log.info("ntfy sent: %s | HTTP %s", title, resp.status)
            return True
    except Exception as e:
        log.error("send_ntfy failed: %s", e)
        return False


def termux_toast(msg: str) -> None:
    try:
        subprocess.run(["termux-toast", "-s", str(msg)], timeout=8, check=False)
    except Exception as e:
        log.warning("termux_toast error: %s", e)


def termux_speak(msg: str) -> None:
    try:
        subprocess.run(["termux-tts-speak", str(msg)], timeout=30, check=False)
    except Exception as e:
        log.warning("termux_speak error: %s", e)


def termux_vibrate(duration: int = 500) -> None:
    try:
        subprocess.run(["termux-vibrate", "-d", str(duration)], timeout=8, check=False)
    except Exception as e:
        log.warning("termux_vibrate error: %s", e)


def write_file(path: str, content: str) -> dict:
    try:
        expanded = os.path.expanduser(path)
        os.makedirs(os.path.dirname(expanded) if os.path.dirname(expanded) else ".", exist_ok=True)
        with open(expanded, "w", encoding="utf-8") as f:
            f.write(content)
        return {"success": True, "path": expanded}
    except Exception as e:
        log.error("write_file error: %s", e)
        return {"success": False, "error": str(e)}


def termux_listen(timeout: int = 10) -> dict:
    """Start microphone listen via termux-microphone-record (basic)."""
    try:
        path = os.path.expanduser("~/bridge_listen.mp4")
        subprocess.run(
            ["termux-microphone-record", "-l", str(timeout), "-f", path],
            timeout=timeout + 5, check=False
        )
        return {"success": True, "file": path}
    except Exception as e:
        log.error("termux_listen error: %s", e)
        return {"success": False, "error": str(e)}


def run_exec(command: str, shell: bool = True) -> dict:
    try:
        result = subprocess.run(
            command,
            shell=shell,
            capture_output=True,
            text=True,
            timeout=30,
        )
        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
        }
    except subprocess.TimeoutExpired:
        return {"stdout": "", "stderr": "Command timed out", "returncode": -1}
    except Exception as e:
        log.error("run_exec error: %s", e)
        return {"stdout": "", "stderr": str(e), "returncode": -1}


# ──────────────────────────────────────────
# TUNNEL CHECK LOOP
# ──────────────────────────────────────────

def tunnel_check_loop() -> None:
    """Background thread: check public URL every TUNNEL_CHECK_INTERVAL seconds.
    Alert via ntfy after TUNNEL_FAIL_THRESHOLD consecutive failures."""
    fail_count = 0
    alerted = False
    log.info("Tunnel check loop started. Monitoring: %s", PUBLIC_URL)

    while True:
        try:
            req = Request(PUBLIC_URL, method="GET")
            with urlopen(req, timeout=15) as resp:
                if resp.status == 200:
                    if fail_count > 0:
                        log.info("Tunnel recovered after %d failures.", fail_count)
                        if alerted:
                            send_ntfy(
                                "✅ BRIDGE TUNNEL RECOVERED",
                                f"Public URL is back online after {fail_count} consecutive failures.\nURL: {PUBLIC_URL}",
                                priority="default",
                                tags="white_check_mark",
                            )
                    fail_count = 0
                    alerted = False
                    log.debug("Tunnel OK")
                else:
                    raise URLError(f"HTTP {resp.status}")
        except Exception as e:
            fail_count += 1
            log.warning("Tunnel check failed (%d/%d): %s", fail_count, TUNNEL_FAIL_THRESHOLD, e)
            if fail_count >= TUNNEL_FAIL_THRESHOLD and not alerted:
                log.error("Tunnel DEAD — sending ntfy alert!")
                send_ntfy(
                    "🚨 BRIDGE TUNNEL DOWN",
                    f"Public URL has failed {fail_count} consecutive health checks.\n"
                    f"URL: {PUBLIC_URL}\nError: {e}\nBridge v{VERSION}",
                    priority="urgent",
                    tags="rotating_light,skull",
                )
                alerted = True

        time.sleep(TUNNEL_CHECK_INTERVAL)


# ──────────────────────────────────────────
# HTTP HANDLER
# ──────────────────────────────────────────

class BridgeHandler(BaseHTTPRequestHandler):

    def log_message(self, fmt, *args):  # redirect to our logger
        log.info("HTTP %s", fmt % args)

    def send_json(self, data: dict, status: int = 200) -> None:
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def send_error_json(self, message: str, status: int = 400) -> None:
        self.send_json({"success": False, "error": message}, status)

    def read_body_json(self) -> dict:
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return {}
        raw = self.rfile.read(length)
        return json.loads(raw.decode("utf-8"))

    # ── GET ────────────────────────────────
    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        params = parse_qs(parsed.query)

        try:
            if path == "/health":
                bat = get_battery()
                self.send_json({
                    "status": "ok",
                    "version": VERSION,
                    "uptime": get_uptime(),
                    "battery": bat["percentage"],
                    "battery_status": bat["status"],
                    "plugged": bat["plugged"],
                    "bridge_alive": True,
                })

            elif path == "/":
                self.send_json({"bridge": "online", "version": VERSION})

            elif path == "/battery":
                self.send_json(get_battery())

            elif path == "/toast":
                msg = params.get("msg", [""])[0]
                if not msg:
                    self.send_error_json("Missing 'msg' query param")
                    return
                termux_toast(msg)
                self.send_json({"success": True, "msg": msg})

            elif path == "/speak":
                msg = params.get("msg", [""])[0]
                if not msg:
                    self.send_error_json("Missing 'msg' query param")
                    return
                threading.Thread(target=termux_speak, args=(msg,), daemon=True).start()
                self.send_json({"success": True, "msg": msg})

            elif path == "/vibrate":
                duration = int(params.get("duration", ["500"])[0])
                termux_vibrate(duration)
                self.send_json({"success": True, "duration": duration})

            elif path == "/listen":
                timeout = int(params.get("timeout", ["10"])[0])
                result = termux_listen(timeout)
                self.send_json(result)

            else:
                self.send_error_json(f"Unknown endpoint: {path}", 404)

        except Exception:
            tb = traceback.format_exc()
            log.error("GET %s unhandled:\n%s", path, tb)
            self.send_error_json("Internal server error", 500)

    # ── POST ───────────────────────────────
    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"

        try:
            body = self.read_body_json()
        except Exception as e:
            self.send_error_json(f"Invalid JSON body: {e}")
            return

        try:
            if path == "/exec":
                command = body.get("command", "")
                if not command:
                    self.send_error_json("Missing 'command' field")
                    return
                result = run_exec(command)
                self.send_json(result)

            elif path == "/toast":
                msg = body.get("msg", "")
                if not msg:
                    self.send_error_json("Missing 'msg' field")
                    return
                termux_toast(msg)
                self.send_json({"success": True, "msg": msg})

            elif path == "/speak":
                msg = body.get("msg", "")
                if not msg:
                    self.send_error_json("Missing 'msg' field")
                    return
                threading.Thread(target=termux_speak, args=(msg,), daemon=True).start()
                self.send_json({"success": True, "msg": msg})

            elif path == "/vibrate":
                duration = int(body.get("duration", 500))
                termux_vibrate(duration)
                self.send_json({"success": True, "duration": duration})

            elif path == "/write_file":
                file_path = body.get("path", "")
                content = body.get("content", "")
                if not file_path:
                    self.send_error_json("Missing 'path' field")
                    return
                result = write_file(file_path, content)
                self.send_json(result)

            elif path == "/listen":
                timeout = int(body.get("timeout", 10))
                result = termux_listen(timeout)
                self.send_json(result)

            elif path == "/conversation":
                msg = body.get("msg", "")
                if not msg:
                    self.send_error_json("Missing 'msg' field")
                    return
                threading.Thread(target=termux_speak, args=(msg,), daemon=True).start()
                termux_toast(msg)
                self.send_json({"success": True, "action": "conversation", "msg": msg})

            elif path == "/voice":
                msg = body.get("msg", "")
                if not msg:
                    self.send_error_json("Missing 'msg' field")
                    return
                termux_vibrate(200)
                threading.Thread(target=termux_speak, args=(msg,), daemon=True).start()
                self.send_json({"success": True, "action": "voice", "msg": msg})

            elif path == "/health":
                bat = get_battery()
                self.send_json({
                    "status": "ok",
                    "version": VERSION,
                    "uptime": get_uptime(),
                    "battery": bat["percentage"],
                    "battery_status": bat["status"],
                    "plugged": bat["plugged"],
                    "bridge_alive": True,
                })

            else:
                self.send_error_json(f"Unknown endpoint: {path}", 404)

        except Exception:
            tb = traceback.format_exc()
            log.error("POST %s unhandled:\n%s", path, tb)
            self.send_error_json("Internal server error", 500)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()


# ──────────────────────────────────────────
# SERVER STARTUP WITH PORT FALLBACK
# ──────────────────────────────────────────

def start_server() -> None:
    port = BASE_PORT
    server = None

    for attempt in range(2):
        try:
            server = HTTPServer(("0.0.0.0", port), BridgeHandler)
            log.info("Bridge v%s listening on port %d", VERSION, port)
            break
        except OSError as e:
            if attempt == 0:
                log.warning("Port %d unavailable (%s). Trying %d ...", port, e, port + 1)
                port += 1
            else:
                log.critical("Could not bind to port %d either. Aborting.", port)
                sys.exit(1)

    # Start tunnel monitor in background
    t = threading.Thread(target=tunnel_check_loop, daemon=True, name="TunnelCheck")
    t.start()

    log.info("Bridge running. Ctrl-C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        log.info("Shutdown requested.")
    finally:
        server.shutdown()
        log.info("Bridge stopped.")


if __name__ == "__main__":
    start_server()
