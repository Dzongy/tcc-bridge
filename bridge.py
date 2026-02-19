#!/usr/bin/env python3
"""
TCC Bridge v7.1 â THE DEFINITIVE PERMANENT BRIDGE
Brain #10 â Kael â Production Edition

Merges v6.0 baseline + v2.0 features into one bulletproof server.
Survives: Reboots, network drops, process kills, Android memory cleanup.

Endpoints (all support GET with query params OR POST with JSON body):
  GET  /health          â Public health check (no auth)
  GET  /status          â Detailed status (auth required)
  POST /exec            â Execute shell command
  POST /toast           â Show toast notification
  POST /vibrate         â Vibrate device
  POST /speak           â Text-to-speech
  POST /listen          â Speech-to-text
  POST /notify          â Push ntfy notification
  POST /push_state      â Manually trigger Supabase state push
  GET  /exec            â Execute command (GET, query: cmd=)
  GET  /toast           â Toast (GET, query: msg=)
  GET  /vibrate         â Vibrate (GET, query: duration=)
  GET  /speak           â Speak (GET, query: msg=)

Auth: Bearer token via:
  - Header:  Authorization: Bearer amos-bridge-2026
  - Header:  Authorization: amos-bridge-2026
  - Query:   ?auth=amos-bridge-2026
  - Body:    {"auth": "amos-bridge-2026"}
"""

import subprocess
import json
import os
import sys
import socket
import signal
import logging
import time
import threading
import traceback
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
from urllib.parse import parse_qs, urlparse

# ââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
# CONFIG
# ââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
AUTH_TOKEN   = os.environ.get("BRIDGE_AUTH",   "amos-bridge-2026")
PORT         = int(os.environ.get("BRIDGE_PORT", "8765"))
SUPABASE_URL = os.environ.get("SUPABASE_URL",  "https://vbqbbziqleymxcyesmky.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY",  "")
NTFY_TOPIC   = os.environ.get("NTFY_TOPIC",    "tcc-zenith-hive")
NTFY_BASE    = "https://ntfy.sh"
PUBLIC_URL   = os.environ.get("PUBLIC_URL",    "https://zenith.cosmic-claw.com")
VERSION      = "7.0.0"
START_TIME   = time.time()
DEVICE_ID    = os.environ.get("DEVICE_ID", socket.gethostname())

# Heartbeat / reporting intervals
HEARTBEAT_SEC  = int(os.environ.get("HEARTBEAT_SEC",  "60"))
REPORT_SEC      = int(os.environ.get("REPORT_SEC",    "300"))
WATCHDOG_SEC    = int(os.environ.get("WATCHDOG_SEC",  "300"))
MAX_RETRIES     = 5
RETRY_BACKOFF   = [2, 4, 8, 16, 32]

# Log setup
LOG_FILE = os.path.expanduser("~/tcc/logs/bridge.log")
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s â %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stderr)
    ]
)
log = logging.getLogger("tcc.bridge.v7")

# Shared stop event for clean shutdown
_stop_event = threading.Event()


# ââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
# UTILITY FUNCTIONS
# ââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
def _run(cmd: str, timeout: int = 15) -> str:
    """Run a shell command and return stdout (stripped). Non-fatal on error."""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True,
            text=True, timeout=timeout
        )
        if result.returncode != 0 and result.stderr:
            log.debug("CMD stderr [%s]: %s", cmd[:60], result.stderr.strip())
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        log.warning("CMD timeout [%s]", cmd[:60])
        return ""
    except Exception as exc:
        log.warning("CMD error [%s]: %s", cmd[:60], exc)
        return ""


def _run_full(cmd: str, timeout: int = 30) -> dict:
    """Run a shell command and return full result dict."""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True,
            text=True, timeout=timeout
        )
        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode
        }
    except subprocess.TimeoutExpired:
        return {"stdout": "", "stderr": "Command timed out.", "returncode": -1}
    except Exception as exc:
        return {"stdout": "", "stderr": str(exc), "returncode": -2}


def _http(method: str, url: str, data: dict = None, headers: dict = None,
          retries: int = MAX_RETRIES) -> dict:
    """Generic HTTP helper with retry + exponential back-off."""
    body = json.dumps(data).encode() if data else None
    _headers = {"Content-Type": "application/json"}
    if headers:
        _headers.update(headers)
    for attempt in range(retries):
        try:
            req = Request(url, data=body, headers=_headers, method=method.upper())
            with urlopen(req, timeout=15) as resp:
                raw = resp.read().decode("utf-8")
                return json.loads(raw) if raw.strip() else {"ok": True}
        except (URLError, HTTPError) as exc:
            wait = RETRY_BACKOFF[min(attempt, len(RETRY_BACKOFF) - 1)]
            log.warning("HTTP %s %s failed (attempt %d/%d): %s. Retrying in %ds.",
                        method, url, attempt + 1, retries, exc, wait)
            if _stop_event.wait(wait):
                break
        except Exception:
            log.error("HTTP unexpected error: %s", traceback.format_exc())
            break
    return {"error": "max_retries_exceeded"}


# ââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
# DEVICE STATE COLLECTORS
# ââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
def get_battery() -> dict:
    try:
        raw = _run("termux-battery-status", timeout=10)
        return json.loads(raw) if raw else {}
    except Exception:
        return {}


def get_storage() -> dict:
    try:
        raw = _run("df /data --output=used,avail,size -m 2>/dev/null | tail -1")
        parts = raw.split()
        if len(parts) >= 3:
            return {
                "used_mb":  int(parts[0]),
                "avail_mb": int(parts[1]),
                "total_mb": int(parts[2])
            }
    except Exception:
        pass
    return {}


def get_network_info() -> dict:
    try:
        ip = _run("ip route get 1 2>/dev/null | awk '{print $NF; exit}'")
        return {"local_ip": ip or "unknown"}
    except Exception:
        return {}


def get_installed_apps() -> list:
    try:
        raw = _run("pm list packages -3 2>/dev/null", timeout=20)
        return [
            line.replace("package:", "").strip()
            for line in raw.splitlines()
            if line.strip()
        ]
    except Exception:
        return []


def build_device_state() -> dict:
    uptime = int(time.time() - START_TIME)
    return {
        "id":         "phone-bridge",
        "device_id":  DEVICE_ID,
        "version":    VERSION,
        "status":     "online",
        "uptime":     uptime,
        "timestamp":  time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "last_seen":  time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "battery":    get_battery(),
        "storage":    get_storage(),
        "network":    get_network_info(),
    }


def build_full_state() -> dict:
    """Full state including app list (slower, used for periodic deep reports)."""
    state = build_device_state()
    state["apps"] = get_installed_apps()
    return state


# ââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
# SUPABASE CLIENT
# ââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
def _supabase_headers() -> dict:
    return {
        "apikey":        SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type":  "application/json",
    }


def supabase_upsert(table: str, payload: dict) -> dict:
    if not SUPABASE_KEY:
        log.debug("SUPABASE_KEY not set â skipping upsert to %s", table)
        return {"skipped": "no_key"}
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    headers = _supabase_headers()
    headers["Prefer"] = "resolution=merge-duplicates,return=minimal"
    result = _http("POST", url, payload, headers)
    if "error" in result:
        log.warning("Supabase upsert to '%s' failed: %s", table, result)
    return result


def supabase_insert(table: str, payload: dict) -> dict:
    if not SUPABASE_KEY:
        log.debug("SUPABASE_KEY not set â skipping insert to %s", table)
        return {"skipped": "no_key"}
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    headers = _supabase_headers()
    headers["Prefer"] = "return=minimal"
    result = _http("POST", url, payload, headers)
    if "error" in result:
        log.warning("Supabase insert to '%s' failed: %s", table, result)
    return result


# ââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
# NTFY CLIENT
# ââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
def ntfy_push(message: str, title: str = "TCC Bridge v7",
              priority=3, tags: list = None) -> dict:
    """Push a notification via ntfy.sh with retry."""
    url = f"{NTFY_BASE}/{NTFY_TOPIC}"
    _tags = ",".join(tags) if tags else "bridge"
    # Normalise priority to string
    prio_str = str(priority) if isinstance(priority, int) else priority
    headers = {
        "Title":    title,
        "Priority": prio_str,
        "Tags":     _tags
    }
    for attempt in range(MAX_RETRIES):
        try:
            req = Request(url, data=message.encode("utf-8"),
                          headers=headers, method="POST")
            with urlopen(req, timeout=10) as resp:
                return {"ok": True, "status": resp.status}
        except Exception as exc:
            wait = RETRY_BACKOFF[min(attempt, len(RETRY_BACKOFF) - 1)]
            log.warning("ntfy push failed (attempt %d/%d): %s. Retry in %ds.",
                        attempt + 1, MAX_RETRIES, exc, wait)
            if _stop_event.wait(wait):
                return {"error": "shutdown_during_retry"}
    return {"error": "ntfy_max_retries"}


# Backwards-compat alias used by v6.0 style code
def ntfy(msg, priority=3, tags=None):
    return ntfy_push(msg, priority=priority, tags=tags)


# ââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
# BACKGROUND THREADS
# ââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
class HeartbeatThread(threading.Thread):
    """Sends periodic heartbeats to ntfy + Supabase."""
    def __init__(self):
        super().__init__(name="heartbeat", daemon=True)
        self._consecutive_failures = 0

    def run(self):
        log.info("Heartbeat thread started (every %ds).", HEARTBEAT_SEC)
        _stop_event.wait(10)  # initial stagger
        while not _stop_event.is_set():
            try:
                bat = get_battery()
                level  = bat.get("percentage", "?")
                status = bat.get("status", "?")
                msg = f"\u{1F493} {DEVICE_ID} | v{VERSION} | Battery: {level}% [{status}]"
                ntfy_push(msg, title="TCC Heartbeat",
                          priority="default", tags=["heartbeat", "white_check_mark"])
                supabase_upsert("heartbeats", {
                    "device_id":   DEVICE_ID,
                    "timestamp":   time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "battery_pct": level,
                    "status":      status,
                    "version":     VERSION
                })
                self._consecutive_failures = 0
                log.info("Heartbeat sent. Battery: %s%%", level)
            except Exception:
                self._consecutive_failures += 1
                log.error("Heartbeat error (#%d): %s",
                          self._consecutive_failures, traceback.format_exc())
                if self._consecutive_failures >= 5:
                    log.critical("5 consecutive heartbeat failures â alerting.")
                    try:
                        ntfy_push(
                            f"CRITICAL: {DEVICE_ID} heartbeat failing â {self._consecutive_failures} consecutive errors!",
                            title="TCC ALERT", priority="urgent", tags=["sos", "warning"]
                        )
                        self._consecutive_failures = 0  # reset after alert
                    except Exception:
                        pass
            _stop_event.wait(HEARTBEAT_SEC)


class ReportThread(threading.Thread):
    """Periodically pushes full device state to Supabase."""
    def __init__(self):
        super().__init__(name="reporter", daemon=True)

    def run(self):
        log.info("Report thread started (every %ds).", REPORT_SEC)
        _stop_event.wait(15)  # stagger from heartbeat
        while not _stop_event.is_set():
            try:
                state = build_full_state()
                # Upsert into device_state table (keyed on id)
                result = supabase_upsert("device_state", state)
                log.info("Device state pushed to Supabase. Result: %s", result)
            except Exception:
                log.error("Report thread error: %s", traceback.format_exc())
            _stop_event.wait(REPORT_SEC)


class WatchdogThread(threading.Thread):
    """Monitors tunnel health and restarts components if needed."""
    def __init__(self):
        super().__init__(name="watchdog", daemon=True)
        self._failures = 0

    def _check_tunnel(self) -> bool:
        """Check if cloudflared process is running (no recursive HTTP call)."""
        try:
            result = subprocess.run(
                ["pgrep", "-f", "cloudflared"],
                capture_output=True, timeout=5
            )
            return result.returncode == 0
        except Exception as exc:
            log.debug("Tunnel process check failed: %s", exc)
            return False

    def _check_local(self) -> bool:
        try:
            req = Request(f"http://localhost:{PORT}/health")
            with urlopen(req, timeout=5) as resp:
                return resp.status == 200
        except Exception:
            return False

    def run(self):
        log.info("Watchdog thread started (every %ds).", WATCHDOG_SEC)
        _stop_event.wait(30)  # let everything start first
        while not _stop_event.is_set():
            try:
                tunnel_ok = self._check_tunnel()
                local_ok  = self._check_local()

                if not tunnel_ok:
                    self._failures += 1
                    log.warning("Watchdog: Tunnel health FAILED (%d consecutive).",
                                self._failures)
                    if self._failures >= 3:
                        msg = (f"\u26A0\uFE0F {DEVICE_ID}: Tunnel health check failed "
                               f"{self._failures}x â check cloudflared.")
                        log.critical(msg)
                        ntfy_push(msg, title="TCC Tunnel ALERT",
                                  priority="urgent", tags=["warning", "cloud"])
                        self._failures = 0
                else:
                    if self._failures > 0:
                        log.info("Watchdog: Tunnel recovered after %d failure(s).",
                                 self._failures)
                    self._failures = 0

                if not local_ok:
                    log.warning("Watchdog: Local health check FAILED.")
                    # PM2 will handle restart; just log it.
                else:
                    log.debug("Watchdog: All checks passed.")

            except Exception:
                log.error("Watchdog thread error: %s", traceback.format_exc())
            _stop_event.wait(WATCHDOG_SEC)


# ââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
# AUTH HELPER
# ââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
def _check_auth(handler, body: dict = None) -> bool:
    """Check auth token from multiple sources. Returns True if valid."""
    # 1. Authorization header
    auth_header = handler.headers.get("Authorization", "")
    if auth_header == AUTH_TOKEN:
        return True
    if auth_header == f"Bearer {AUTH_TOKEN}":
        return True
    # 2. X-Auth header
    x_auth = handler.headers.get("X-Auth", "")
    if x_auth == AUTH_TOKEN:
        return True
    # 3. Query parameter
    parsed = urlparse(handler.path)
    query  = parse_qs(parsed.query)
    if query.get("auth", [None])[0] == AUTH_TOKEN:
        return True
    # 4. JSON body field
    if body and body.get("auth") == AUTH_TOKEN:
        return True
    return False


# ââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
# HTTP HANDLER
# ââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
class BridgeHandler(BaseHTTPRequestHandler):
    server_version = f"TCC-Bridge/{VERSION}"
    protocol_version = "HTTP/1.1"

    # ââ Logging ââ
    def log_message(self, fmt, *args):
        log.info("%s â %s", self.client_address[0], fmt % args)

    def log_error(self, fmt, *args):
        log.warning("%s â %s", self.client_address[0], fmt % args)

    # ââ Response helpers ââ
    def _send_json(self, code: int, obj: dict):
        body = json.dumps(obj, default=str).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Bridge-Version", VERSION)
        self.end_headers()
        try:
            self.wfile.write(body)
        except BrokenPipeError:
            pass

    def _send_ok(self, extra: dict = None):
        data = {"ok": True}
        if extra:
            data.update(extra)
        self._send_json(200, data)

    def _send_error_json(self, code: int, message: str):
        self._send_json(code, {"ok": False, "error": message, "code": code})

    # ââ Body reader ââ
    def _read_body(self) -> dict:
        try:
            length = int(self.headers.get("Content-Length", 0))
            if length > 0:
                raw = self.rfile.read(length).decode("utf-8")
                try:
                    return json.loads(raw)
                except json.JSONDecodeError:
                    return {"_raw": raw}
        except Exception as exc:
            log.debug("Body read error: %s", exc)
        return {}

    # ââ Path + query helpers ââ
    def _path(self) -> str:
        return urlparse(self.path).path

    def _query(self) -> dict:
        return parse_qs(urlparse(self.path).query)

    def _qget(self, key: str, default=None):
        return self._query().get(key, [default])[0]

    # ââââââââââââââââââââââââââââââââââââââââââââ
    # GET HANDLER
    # ââââââââââââââââââââââââââââââââââââââââââââ
    def do_GET(self):
        path = self._path()

        # ââ Public: /health ââ
        if path == "/health":
            uptime = int(time.time() - START_TIME)
            bat    = get_battery()
            self._send_json(200, {
                "status":    "online",
                "version":   VERSION,
                "device_id": DEVICE_ID,
                "uptime":    uptime,
                "battery":   bat,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            })
            return

        # ââ All other routes require auth ââ
        if not _check_auth(self):
            self._send_error_json(401, "Unauthorized â provide valid auth token.")
            return

        if path == "/status":
            uptime = int(time.time() - START_TIME)
            self._send_json(200, {
                "status":    "online",
                "version":   VERSION,
                "device_id": DEVICE_ID,
                "uptime":    uptime,
                "battery":   get_battery(),
                "storage":   get_storage(),
                "network":   get_network_info(),
                "port":      PORT,
                "public_url": PUBLIC_URL,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            })

        elif path == "/exec":
            cmd = self._qget("cmd")
            if not cmd:
                self._send_error_json(400, "Missing required query param: cmd")
                return
            log.info("EXEC (GET): %s", cmd)
            result = _run_full(cmd)
            self._send_json(200, {
                "ok":         result["returncode"] == 0,
                "stdout":     result["stdout"],
                "stderr":     result["stderr"],
                "returncode": result["returncode"],
                "cmd":        cmd
            })

        elif path == "/toast":
            msg = self._qget("msg", "Hello from TCC Bridge")
            _run(f'termux-toast {json.dumps(msg)}')
            self._send_ok({"message": "Toast sent", "msg": msg})

        elif path == "/vibrate":
            try:
                duration = max(10, min(int(self._qget("duration", "500")), 5000))
            except (ValueError, TypeError):
                duration = 500
            _run(f"termux-vibrate -d {duration}")
            self._send_ok({"message": "Vibrated", "duration": duration})

        elif path == "/speak":
            msg  = self._qget("msg", "Hello")
            lang = self._qget("lang", "en")
            _run(f"termux-tts-speak -l {lang} {json.dumps(msg)}")
            self._send_ok({"message": "Speaking", "text": msg})

        else:
            self._send_error_json(404, f"Endpoint not found: {path}")

    # ââââââââââââââââââââââââââââââââââââââââââââ
    # POST HANDLER
    # ââââââââââââââââââââââââââââââââââââââââââââ
    def do_POST(self):
        path = self._path()
        body = self._read_body()

        # ââ Public: /health (POST) ââ
        if path == "/health":
            uptime = int(time.time() - START_TIME)
            self._send_json(200, {
                "status":    "online",
                "version":   VERSION,
                "uptime":    uptime,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            })
            return

        # ââ Auth required for all POST routes ââ
        if not _check_auth(self, body):
            self._send_error_json(401, "Unauthorized â provide valid auth token.")
            return

        if path == "/exec":
            # Support both 'cmd' (v7) and 'command' (v2 legacy)
            cmd = body.get("cmd") or body.get("command", "")
            if not cmd:
                self._send_error_json(400, "Missing required field: 'cmd'")
                return
            timeout = int(body.get("timeout", 30))
            log.info("EXEC (POST): %s", cmd)
            result = _run_full(cmd, timeout=timeout)
            self._send_json(200, {
                "ok":         result["returncode"] == 0,
                "stdout":     result["stdout"],
                "stderr":     result["stderr"],
                "returncode": result["returncode"],
                "cmd":        cmd
            })

        elif path == "/toast":
            msg = body.get("msg") or body.get("message", "")
            if not msg:
                self._send_error_json(400, "Missing required field: 'msg'")
                return
            _run(f'termux-toast {json.dumps(msg)}')
            self._send_ok({"message": "Toast sent", "msg": msg})

        elif path == "/vibrate":
            try:
                duration = max(10, min(int(body.get("duration", 500)), 5000))
            except (ValueError, TypeError):
                duration = 500
            _run(f"termux-vibrate -d {duration}")
            self._send_ok({"message": "Vibrated", "duration": duration})

        elif path == "/speak":
            text = body.get("text") or body.get("msg", "")
            lang = body.get("lang", "en")
            if not text:
                self._send_error_json(400, "Missing required field: 'text'")
                return
            _run(f"termux-tts-speak -l {lang} {json.dumps(text)}")
            self._send_ok({"message": "Speaking", "text": text})

        elif path == "/listen":
            lang    = body.get("lang", "en-US")
            timeout = int(body.get("timeout", 5))
            raw = _run(f"termux-speech-to-text -l {lang}", timeout=timeout + 10)
            try:
                parsed = json.loads(raw)
            except Exception:
                parsed = {"transcript": raw}
            self._send_json(200, parsed)

        elif path == "/notify":
            msg      = body.get("msg") or body.get("message", "")
            title    = body.get("title", "TCC Bridge v7")
            priority = body.get("priority", "default")
            tags     = body.get("tags", [])
            if not msg:
                self._send_error_json(400, "Missing required field: 'msg'")
                return
            result = ntfy_push(msg, title=title, priority=priority, tags=tags)
            self._send_json(200, result)

        elif path in ("/push_state", "/state-push"):
            # Trigger an immediate Supabase state push
            try:
                state  = build_full_state()
                result = supabase_upsert("device_state", state)
                log.info("Manual push_state triggered. Result: %s", result)
                self._send_json(200, {"ok": True, "state": state, "supabase": result})
            except Exception as exc:
                log.error("push_state error: %s", traceback.format_exc())
                self._send_error_json(500, f"push_state failed: {exc}")

        else:
            self._send_error_json(404, f"Endpoint not found: {path}")

    # ââââââââââââââââââââââââââââââââââââââââââââ
    # OPTIONS (CORS pre-flight)
    # ââââââââââââââââââââââââââââââââââââââââââââ
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Allow", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers",
                         "Authorization, Content-Type, X-Auth")
        self.send_header("Content-Length", "0")
        self.end_headers()


# ââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
# SIGNAL HANDLING
# ââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
def _handle_signal(sig, frame):
    log.info("Signal %s received â initiating graceful shutdown.", sig)
    _stop_event.set()


# ââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
# SERVER BOOTSTRAP
# ââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
def run_server():
    # Register signal handlers
    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT,  _handle_signal)

    # Start background threads
    threads = [
        HeartbeatThread(),
        ReportThread(),
        WatchdogThread(),
    ]
    for t in threads:
        t.start()
        log.info("Started thread: %s", t.name)

    # Send startup notification
    try:
        ntfy_push(
            f"\U0001F680 TCC Bridge v{VERSION} started on {DEVICE_ID} | Port: {PORT}",
            title="Bridge Online",
            priority="high",
            tags=["rocket", "shield"]
        )
    except Exception:
        log.warning("Startup ntfy failed (non-fatal).")

    # Push initial state
    try:
        state = build_device_state()
        supabase_upsert("device_state", state)
        log.info("Initial state pushed to Supabase.")
    except Exception:
        log.warning("Initial Supabase push failed (non-fatal).")

    # Bind with retry
    server = None
    for attempt in range(10):
        try:
            server = HTTPServer(("0.0.0.0", PORT), BridgeHandler)
            server.socket.setsockopt(
                __import__('socket').SOL_SOCKET,
                __import__('socket').SO_REUSEADDR, 1
            )
            log.info("TCC Bridge v%s listening on 0.0.0.0:%d", VERSION, PORT)
            break
        except OSError as exc:
            wait = RETRY_BACKOFF[min(attempt, len(RETRY_BACKOFF) - 1)]
            log.error("Server bind error (attempt %d/10): %s. Retrying in %ds.",
                      attempt + 1, exc, wait)
            time.sleep(wait)

    if server is None:
        log.critical("Failed to bind server after 10 attempts. Exiting.")
        sys.exit(1)

    try:
        server.serve_forever()
    except Exception:
        log.critical("Server crashed: %s", traceback.format_exc())
    finally:
        _stop_event.set()
        server.server_close()
        log.info("Server closed.")
        try:
            ntfy_push(
                f"\u26A0\uFE0F TCC Bridge v{VERSION} STOPPED on {DEVICE_ID}",
                title="Bridge Offline",
                priority="urgent",
                tags=["warning", "sos"]
            )
        except Exception:
            pass
        log.info("TCC Bridge v%s shutdown complete.", VERSION)


if __name__ == "__main__":
    log.info("============================================================")
    log.info("=== TCC Bridge v%s starting | Device: %s | Port: %d ===",
             VERSION, DEVICE_ID, PORT)
    log.info("  AUTH_TOKEN : %s", AUTH_TOKEN)
    log.info("  SUPABASE   : %s", SUPABASE_URL)
    log.info("  NTFY_TOPIC : %s", NTFY_TOPIC)
    log.info("  PUBLIC_URL : %s", PUBLIC_URL)
    log.info("============================================================")
    run_server()
