#!/usr/bin/env python3
"""
TCC Bridge V2 - Unified Server + Push Reporting
Supabase URL: https://vbqbbziqleymxcyesmky.supabase.co
ntfy topic: zenith-escape
"""

import os
import json
import time
import threading
import subprocess
import logging
import traceback
import socket
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
from urllib.parse import urlparse
import urllib.request

# ─── CONFIG ────────────────────────────────────────────────────────────────────
SUPABASE_URL     = "https://vbqbbziqleymxcyesmky.supabase.co"
SUPABASE_KEY     = "sb_secret_lIbl-DBgdnrt_fejgJjKqg_qR62SVEm"
NTFY_TOPIC       = "zenith-escape"
NTFY_BASE        = "https://ntfy.sh"
SERVER_PORT      = 8765
PUBLIC_URL       = "https://zenith.cosmic-claw.com"
HEARTBEAT_SEC    = 60       # seconds between heartbeats
REPORT_SEC       = 120      # seconds between full state pushes
MAX_RETRIES      = 5
RETRY_BACKOFF    = [2, 4, 8, 16, 32]  # exponential back-off
DEVICE_ID        = socket.gethostname()

# ─── LOGGING ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.expanduser("~/tcc-bridge-v2.log"), encoding="utf-8")
    ]
)
log = logging.getLogger("bridge_v2")

# ─── WATCHDOG ───────────────────────────────────────────────────────────────────
def check_tunnel_health():
    """Check if the public URL is reachable."""
    try:
        req = Request(f"{PUBLIC_URL}/health", headers={'User-Agent': 'TCC-Bridge-Watchdog'})
        with urlopen(req, timeout=10) as response:
            return response.getcode() == 200
    except Exception:
        return False

def watchdog_loop():
    """Background thread to monitor tunnel and processes."""
    while True:
        time.sleep(300) # Check every 5 mins
        if not check_tunnel_health():
            msg = "⚠️ Bridge Public Health Check FAILED. Tunnel might be down."
            log.warning(msg)
            publish_ntfy(msg, priority=4, tags=["warning", "bridge"])
            # In PM2 environment, we expect PM2 to handle restarts of cloudflared
            # but we can trigger a self-restart or just alert.

# ─── HELPERS ───────────────────────────────────────────────────────────────────
def _run(cmd: str, timeout: int = 15) -> str:
    """Run a shell command and return stdout (stripped)."""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=timeout
        )
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        log.warning("Command timed out: %s", cmd)
        return ""
    except Exception as e:
        log.warning("Command error (%s): %s", cmd, e)
        return ""


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
            with urlopen(req, timeout=10) as resp:
                raw = resp.read().decode("utf-8")
                return json.loads(raw) if raw.strip() else {"ok": True}
        except (URLError, HTTPError) as e:
            wait = RETRY_BACKOFF[min(attempt, len(RETRY_BACKOFF) - 1)]
            log.warning("HTTP %s %s failed (attempt %d/%d): %s. Retrying in %ds.",
                        method, url, attempt + 1, retries, e, wait)
            time.sleep(wait)
        except Exception as e:
            log.error("Unexpected HTTP error: %s", traceback.format_exc())
            break
    return {"error": "max_retries_exceeded"}


# ─── DEVICE STATE ──────────────────────────────────────────────────────────────
def get_battery() -> dict:
    """Return battery level + charging status."""
    try:
        raw = _run("termux-battery-status")
        return json.loads(raw) if raw else {}
    except Exception:
        return {}


def get_storage() -> dict:
    """Return internal storage free/total in MB."""
    try:
        raw = _run("df /data --output=used,avail,size -m | tail -1")
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


def get_installed_apps() -> list:
    """Return list of installed user packages."""
    try:
        raw = _run("pm list packages -3", timeout=20)
        pkgs = [line.replace("package:", "").strip() for line in raw.splitlines() if line.strip()]
        return pkgs
    except Exception:
        return []


def get_network_info() -> dict:
    """Return basic network info."""
    try:
        ip = _run("ip route get 1 | awk '{print $NF; exit}'")
        return {"local_ip": ip}
    except Exception:
        return {}


def build_device_state() -> dict:
    """Assemble full device state payload."""
    battery = get_battery()
    storage = get_storage()
    apps    = get_installed_apps()
    network = get_network_info()
    return {
        "device_id":  DEVICE_ID,
        "timestamp":  time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "battery":    battery,
        "storage":    storage,
        "apps":       apps,
        "network":    network
    }


# ─── SUPABASE CLIENT ───────────────────────────────────────────────────────────
def supabase_upsert(table: str, payload: dict) -> dict:
    """Upsert a row into a Supabase table."""
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    headers = {
        "apikey":        SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Prefer":        "resolution=merge-duplicates,return=minimal"
    }
    return _http("POST", url, payload, headers)


def supabase_insert(table: str, payload: dict) -> dict:
    """Insert a row into a Supabase table."""
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    headers = {
        "apikey":        SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Prefer":        "return=minimal"
    }
    return _http("POST", url, payload, headers)


# ─── NTFY CLIENT ───────────────────────────────────────────────────────────────
def ntfy_push(message: str, title: str = "TCC Bridge", priority: str = "default",
              tags: list = None) -> dict:
    """Push a notification via ntfy."""
    url = f"{NTFY_BASE}/{NTFY_TOPIC}"
    body = message.encode()
    _tags = ",".join(tags) if tags else "bridge"
    headers = {
        "Title":    title,
        "Priority": priority,
        "Tags":     _tags
    }
    for attempt in range(MAX_RETRIES):
        try:
            req = Request(url, data=body, headers=headers, method="POST")
            with urlopen(req, timeout=10) as resp:
                return {"ok": True, "status": resp.status}
        except Exception as e:
            wait = RETRY_BACKOFF[min(attempt, len(RETRY_BACKOFF) - 1)]
            log.warning("ntfy push failed (attempt %d): %s. Retry in %ds.", attempt + 1, e, wait)
            time.sleep(wait)
    return {"error": "ntfy_failed"}


# ─── BACKGROUND TASKS ──────────────────────────────────────────────────────────
_stop_event = threading.Event()


def heartbeat_loop():
    """Send periodic heartbeats to ntfy and Supabase."""
    log.info("Heartbeat loop started (every %ds).", HEARTBEAT_SEC)
    while not _stop_event.is_set():
        try:
            bat = get_battery()
            level = bat.get("percentage", "?")
            status = bat.get("status", "?")
            msg = f"💓 {DEVICE_ID} | Battery: {level}% [{status}]"
            ntfy_push(msg, title="TCC Heartbeat", tags=["heartbeat", "white_check_mark"])
            supabase_upsert("heartbeats", {
                "device_id":  DEVICE_ID,
                "timestamp":  time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "battery_pct": level,
                "status":     status
            })
            log.info("Heartbeat sent. Battery: %s%%", level)
        except Exception:
            log.error("Heartbeat error: %s", traceback.format_exc())
        _stop_event.wait(HEARTBEAT_SEC)


def report_loop():
    """Push full device state to Supabase periodically."""
    log.info("Report loop started (every %ds).", REPORT_SEC)
    # Initial delay to stagger from heartbeat
    _stop_event.wait(15)
    while not _stop_event.is_set():
        try:
            state = build_device_state()
            result = supabase_upsert("device_state", state)
            log.info("Device state pushed to Supabase. Result: %s", result)
        except Exception:
            log.error("Report loop error: %s", traceback.format_exc())
        _stop_event.wait(REPORT_SEC)


# ─── HTTP SERVER ───────────────────────────────────────────────────────────────
class BridgeHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path == "/exec":
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            try:
                data = json.loads(post_data)
                command = data.get("command")
                # Basic auth check
                if data.get("auth") != SUPABASE_KEY:
                     self.send_response(401)
                     self.end_headers()
                     return
                
                result = subprocess.check_output(command, shell=True, stderr=subprocess.STDOUT, timeout=30)
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"output": result.decode()}).encode())
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(str(e).encode())
            return


    def log_message(self, format, *args):  # silence default access log
        log.debug("HTTP %s", format % args)

    def _send_json(self, code: int, obj: dict):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self) -> dict:
        length = int(self.headers.get("Content-Length", 0))
        if length:
            raw = self.rfile.read(length).decode("utf-8")
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                return {"raw": raw}
        return {}

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/health":
            bat = get_battery()
            self._send_json(200, {
                "status":    "ok",
                "device_id": DEVICE_ID,
                "battery":   bat,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            })
        else:
            self._send_json(404, {"error": "not_found", "path": path})

    def do_POST(self):
        path = urlparse(self.path).path
        body = self._read_body()

        if path == "/exec":
            cmd = body.get("cmd", "")
            if not cmd:
                return self._send_json(400, {"error": "missing 'cmd'"})
            log.info("EXEC: %s", cmd)
            out = _run(cmd, timeout=30)
            self._send_json(200, {"output": out})

        elif path == "/toast":
            msg = body.get("msg", body.get("message", ""))
            if not msg:
                return self._send_json(400, {"error": "missing 'msg'"})
            _run(f'termux-toast -s {json.dumps(msg)}')
            self._send_json(200, {"ok": True, "msg": msg})

        elif path == "/speak":
            text = body.get("text", "")
            lang = body.get("lang", "en")
            if not text:
                return self._send_json(400, {"error": "missing 'text'"})
            _run(f'termux-tts-speak -l {lang} {json.dumps(text)}')
            self._send_json(200, {"ok": True, "text": text})

        elif path == "/vibrate":
            duration = int(body.get("duration", 500))
            duration = max(10, min(duration, 5000))
            _run(f'termux-vibrate -d {duration}')
            self._send_json(200, {"ok": True, "duration": duration})

        elif path == "/listen":
            lang    = body.get("lang", "en-US")
            timeout = int(body.get("timeout", 5))
            raw     = _run(f'termux-speech-to-text -l {lang}', timeout=timeout + 10)
            try:
                parsed = json.loads(raw)
            except Exception:
                parsed = {"transcript": raw}
            self._send_json(200, parsed)

        elif path == "/notify":
            msg      = body.get("msg", body.get("message", ""))
            title    = body.get("title", "TCC Bridge")
            priority = body.get("priority", "default")
            tags     = body.get("tags", [])
            if not msg:
                return self._send_json(400, {"error": "missing 'msg'"})
            result = ntfy_push(msg, title=title, priority=priority, tags=tags)
            self._send_json(200, result)

        elif path == "/push_state":
            state  = build_device_state()
            result = supabase_upsert("device_state", state)
            self._send_json(200, {"ok": True, "state": state, "supabase": result})

        else:
            self._send_json(404, {"error": "not_found", "path": path})


def start_server():
    """Start the HTTP server with retry on bind failure."""
    for attempt in range(10):
        try:
            server = HTTPServer(("", SERVER_PORT), BridgeHandler)
            log.info("TCC Bridge V2 listening on port %d", SERVER_PORT)
            server.serve_forever()
            break
        except OSError as e:
            wait = RETRY_BACKOFF[min(attempt, len(RETRY_BACKOFF) - 1)]
            log.error("Server bind error (attempt %d): %s. Retrying in %ds.", attempt + 1, e, wait)
            time.sleep(wait)
        except Exception:
            log.critical("Fatal server error: %s", traceback.format_exc())
            break


# ─── ENTRY POINT ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    log.info("=== TCC Bridge V2 starting. Device: %s ===", DEVICE_ID)

    # Send startup notification
    try:
        ntfy_push(
            f"🚀 TCC Bridge V2 started on {DEVICE_ID}",
            title="Bridge Online",
            priority="high",
            tags=["rocket", "white_check_mark"]
        )
    except Exception:
        log.warning("Startup ntfy failed (non-fatal).")

    # Start background threads
    hb_thread = threading.Thread(target=heartbeat_loop, daemon=True, name="heartbeat")
    rp_thread = threading.Thread(target=report_loop,    daemon=True, name="reporter")
    hb_thread.start()
    rp_thread.start()
    log.info("Background threads started.")

    # Start HTTP server (blocking)
    try:
        start_server()
    except KeyboardInterrupt:
        log.info("Shutdown requested.")
    finally:
        _stop_event.set()
        ntfy_push(f"⚠️ TCC Bridge V2 STOPPED on {DEVICE_ID}",
                  title="Bridge Offline", priority="urgent", tags=["warning"])
        log.info("Bridge V2 stopped.")
