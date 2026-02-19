#!/usr/bin/env python3
# =============================================================================
# TCC Master Bridge v6.0.0
# Permanent, bulletproof bridge for Termux + Cloudflare + Supabase
# =============================================================================

import json
import logging
import os
import subprocess
import sys
import threading
import time
import traceback
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import List
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlparse
from urllib.request import Request, urlopen

# =============================================================================
# LOGGING SETUP
# =============================================================================

LOG_DIR = os.path.expanduser("~/tcc-bridge/logs")
os.makedirs(LOG_DIR, exist_ok=True)
log_path = os.path.join(LOG_DIR, "bridge.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(log_path),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("bridge")

# =============================================================================
# CONFIGURATION
# =============================================================================

VERSION = "6.0.0"

# HTTP Server
BASE_PORT = int(os.environ.get("BRIDGE_PORT", 8765))

# Supabase
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://vbqbbziqleymxcyesmky.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "sb_secret_lIbl-DBgdnrt_fejgJjKqg_qR62SVEm")
SUPABASE_TABLE = "device_state"

# Device identity
DEVICE_ID = os.environ.get("DEVICE_ID", "amos-arms")

# ntfy
NTFY_BRIDGE_URL = os.environ.get("NTFY_BRIDGE_URL", "https://ntfy.sh/tcc-zenith-hive")
NTFY_PUSH_URL = os.environ.get("NTFY_PUSH_URL", "https://ntfy.sh/zenith-escape")

# Tunnel
PUBLIC_URL = os.environ.get("BRIDGE_PUBLIC_URL", "https://zenith.cosmic-claw.com/health")
TUNNEL_CHECK_INTERVAL = int(os.environ.get("TUNNEL_CHECK_INTERVAL", 120))
TUNNEL_FAIL_THRESHOLD = int(os.environ.get("TUNNEL_FAIL_THRESHOLD", 3))

# Cloudflared
CLOUDFLARED_UUID = os.environ.get("CLOUDFLARED_UUID", "18ba1a49-fdf9-4a52-a27a-5250d397c5c5")
CLOUDFLARED_CHECK_INTERVAL = int(os.environ.get("CLOUDFLARED_CHECK_INTERVAL", 60))

# Heartbeat / state push interval in seconds
HEARTBEAT_INTERVAL = int(os.environ.get("HEARTBEAT_INTERVAL", 300))

# Time the process started
START_TIME = time.time()

# Global restart counter for cloudflared
_cloudflared_restart_count = 0

# =============================================================================
# SHELL UTILITIES
# =============================================================================

def run_shell(cmd: str, timeout: int = 30) -> str:
    """Execute a shell command and return combined stdout/stderr."""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=timeout
        )
        return result.stdout.strip() or result.stderr.strip() or ""
    except subprocess.TimeoutExpired:
        log.warning("run_shell timeout: %s", cmd)
        return ""
    except Exception as e:
        log.error("run_shell error [%s]: %s", cmd, e)
        return ""


def run_exec(command: str, shell: bool = True) -> dict:
    """Execute a command and return a structured result dict."""
    try:
        result = subprocess.run(
            command, shell=shell, capture_output=True, text=True, timeout=60
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


# =============================================================================
# DEVICE STATE COLLECTORS
# =============================================================================

def get_uptime() -> float:
    """Return bridge process uptime in seconds."""
    return round(time.time() - START_TIME, 2)


def get_battery() -> dict:
    """Get battery info via termux-battery-status, falling back to dumpsys."""
    # Primary: termux-battery-status (JSON)
    try:
        result = subprocess.run(
            ["termux-battery-status"], capture_output=True, text=True, timeout=8
        )
        data = json.loads(result.stdout)
        return {
            "percentage": data.get("percentage", -1),
            "plugged": data.get("plugged", "UNKNOWN"),
            "status": data.get("status", "UNKNOWN"),
        }
    except Exception:
        pass

    # Fallback: dumpsys battery
    try:
        output = run_shell("dumpsys battery")
        info: dict = {"percentage": -1, "plugged": "UNKNOWN", "status": "UNKNOWN"}
        for line in output.splitlines():
            line = line.strip()
            if line.startswith("level:"):
                try:
                    info["percentage"] = int(line.split(":")[1].strip())
                except Exception:
                    pass
            elif line.startswith("status:"):
                info["status"] = line.split(":")[1].strip()
            elif line.startswith("plugged:"):
                info["plugged"] = line.split(":")[1].strip()
        return info
    except Exception as e:
        log.warning("get_battery fallback failed: %s", e)
        return {"percentage": -1, "plugged": "UNKNOWN", "status": "UNKNOWN"}


def get_network() -> str:
    """Detect current network type (wifi / mobile / offline)."""
    try:
        wifi = run_shell("dumpsys wifi | grep 'Wi-Fi is' | head -1")
        if "enabled" in wifi.lower():
            ssid_line = run_shell("dumpsys wifi | grep 'SSID:' | head -1")
            ssid = ssid_line.split(":")[1].strip() if ":" in ssid_line else "unknown"
            return f"wifi:{ssid}"
        mobile = run_shell(
            "dumpsys telephony.registry | grep 'mDataConnectionState' | head -1"
        )
        if "2" in mobile:
            return "mobile:data"
        return "offline"
    except Exception as e:
        log.warning("get_network error: %s", e)
        return "unknown"


def get_storage() -> dict:
    """Get /data storage usage."""
    try:
        output = run_shell("df -h /data")
        lines = output.splitlines()
        if len(lines) > 1:
            parts = lines[1].split()
            if len(parts) >= 5:
                return {
                    "size": parts[1],
                    "used": parts[2],
                    "available": parts[3],
                    "use_percent": parts[4],
                }
    except Exception as e:
        log.warning("get_storage error: %s", e)
    return {}


def get_installed_apps(limit: int = 100) -> List[str]:
    """Return list of installed Android package names."""
    try:
        output = run_shell("pm list packages")
        apps = []
        for line in output.splitlines():
            if line.startswith("package:"):
                apps.append(line.replace("package:", "").strip())
        return apps[:limit]
    except Exception as e:
        log.warning("get_installed_apps error: %s", e)
        return []


def get_device_meta() -> dict:
    """Return Android device metadata."""
    try:
        return {
            "android_version": run_shell("getprop ro.build.version.release"),
            "hostname": run_shell("hostname"),
            "model": run_shell("getprop ro.product.model"),
            "termux_version": run_shell(
                "termux-info 2>/dev/null | head -1 || echo unknown"
            ),
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        log.warning("get_device_meta error: %s", e)
        return {}


def build_full_state() -> dict:
    """Assemble a complete device state snapshot."""
    battery = get_battery()
    meta = get_device_meta()
    storage = get_storage()
    network = get_network()
    now_iso = datetime.utcnow().isoformat()

    return {
        # Primary Supabase columns
        "device_id": DEVICE_ID,
        "status": "online",
        "last_seen": now_iso,
        # Rich metadata (stored in 'metadata' jsonb column)
        "metadata": {
            "bridge_version": VERSION,
            "uptime": get_uptime(),
            "battery_level": battery.get("percentage", -1),
            "battery_status": battery.get("status", "UNKNOWN"),
            "battery_plugged": battery.get("plugged", "UNKNOWN"),
            "network": network,
            "storage": storage,
            "android_version": meta.get("android_version", ""),
            "hostname": meta.get("hostname", ""),
            "model": meta.get("model", ""),
            "termux_version": meta.get("termux_version", ""),
            "cloudflared_restarts": _cloudflared_restart_count,
            "timestamp": now_iso,
        },
    }


# =============================================================================
# TERMUX ACTIONS
# =============================================================================

def termux_toast(msg: str) -> None:
    """Show a short Android toast notification."""
    try:
        subprocess.run(["termux-toast", "-s", str(msg)], timeout=8, check=False)
    except Exception as e:
        log.warning("termux_toast error: %s", e)


def termux_speak(msg: str) -> None:
    """Speak a message via TTS (blocking)."""
    try:
        subprocess.run(["termux-tts-speak", str(msg)], timeout=30, check=False)
    except Exception as e:
        log.warning("termux_speak error: %s", e)


def termux_vibrate(duration: int = 500) -> None:
    """Vibrate the device for 'duration' milliseconds."""
    try:
        subprocess.run(
            ["termux-vibrate", "-d", str(duration)], timeout=8, check=False
        )
    except Exception as e:
        log.warning("termux_vibrate error: %s", e)


def termux_listen(timeout: int = 10) -> dict:
    """Record audio via termux-microphone-record."""
    try:
        path = os.path.expanduser("~/bridge_listen.mp4")
        subprocess.run(
            ["termux-microphone-record", "-l", str(timeout), "-f", path],
            timeout=timeout + 5,
            check=False,
        )
        return {"success": True, "file": path}
    except Exception as e:
        log.error("termux_listen error: %s", e)
        return {"success": False, "error": str(e)}


def write_file(path: str, content: str) -> dict:
    """Write content to a file, creating directories as needed."""
    try:
        expanded = os.path.expanduser(path)
        parent = os.path.dirname(expanded)
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(expanded, "w", encoding="utf-8") as f:
            f.write(content)
        return {"success": True, "path": expanded}
    except Exception as e:
        log.error("write_file error: %s", e)
        return {"success": False, "error": str(e)}


# =============================================================================
# NTFY HELPERS
# =============================================================================

def send_ntfy(
    title: str,
    message: str,
    priority: str = "default",
    tags: str = "bridge",
    url: str = "",
) -> bool:
    """Send a push notification via ntfy using stdlib urllib (zero extra deps)."""
    target = url or NTFY_BRIDGE_URL
    try:
        req = Request(
            target,
            data=message.encode("utf-8"),
            headers={
                "Title": title,
                "Priority": priority,
                "Tags": tags,
            },
            method="POST",
        )
        with urlopen(req, timeout=10) as resp:
            log.info("ntfy sent [%s]: HTTP %s", title, resp.status)
            return True
    except Exception as e:
        log.error("send_ntfy failed [%s]: %s", title, e)
        return False


# =============================================================================
# SUPABASE PUSH
# Upserts into device_state table with columns:
#   device_id TEXT (primary key)
#   status    TEXT
#   last_seen TIMESTAMPTZ
#   metadata  JSONB
# =============================================================================

def push_to_supabase(payload: dict) -> bool:
    """Upsert device state into Supabase via REST API."""
    endpoint = f"{SUPABASE_URL}/rest/v1/{SUPABASE_TABLE}"
    body = json.dumps(payload, default=str).encode("utf-8")
    try:
        req = Request(
            endpoint,
            data=body,
            headers={
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}",
                "Content-Type": "application/json",
                # Upsert: merge on conflict, return nothing (faster)
                "Prefer": "resolution=merge-duplicates,return=minimal",
            },
            method="POST",
        )
        with urlopen(req, timeout=15) as resp:
            log.info("Supabase push OK: HTTP %s", resp.status)
            return True
    except HTTPError as e:
        body_text = e.read().decode(errors="replace")
        log.error("Supabase HTTP error %s: %s", e.code, body_text)
        return False
    except Exception as e:
        log.error("Supabase push failed: %s", e)
        return False


# =============================================================================
# HEALTH CHECK HELPER (used internally and by /health endpoint)
# =============================================================================

def check_health() -> dict:
    """Build a rich health snapshot for the /health endpoint."""
    bat = get_battery()
    return {
        "status": "ok",
        "bridge": "online",
        "version": VERSION,
        "device_id": DEVICE_ID,
        "uptime_seconds": get_uptime(),
        "battery_level": bat["percentage"],
        "battery_status": bat["status"],
        "battery_plugged": bat["plugged"],
        "network": get_network(),
        "bridge_alive": True,
        "cloudflared_restarts": _cloudflared_restart_count,
        "timestamp": datetime.utcnow().isoformat(),
    }


# =============================================================================
# HEARTBEAT PUSH LOOP
# =============================================================================

def heartbeat_loop() -> None:
    """Background thread: push device state to Supabase + ntfy every HEARTBEAT_INTERVAL seconds."""
    log.info("Heartbeat loop started. Interval: %ds", HEARTBEAT_INTERVAL)
    while True:
        try:
            state = build_full_state()

            # Push to Supabase
            sb_ok = push_to_supabase(state)

            # Build readable summary for ntfy
            meta = state.get("metadata", {})
            battery_level = meta.get("battery_level", "?")
            network = meta.get("network", "unknown")
            storage = meta.get("storage", {})
            use_pct = storage.get("use_percent", "?")
            uptime_s = meta.get("uptime", 0)
            msg = (
                f"Device: {DEVICE_ID}\n"
                f"Battery: {battery_level}% | Network: {network}\n"
                f"Storage used: {use_pct} | Uptime: {uptime_s}s\n"
                f"Bridge v{VERSION}"
            )
            ntfy_ok = send_ntfy(
                title=f"\U0001f4e1 TCC Heartbeat \u2014 {datetime.utcnow().strftime('%H:%M UTC')}",
                message=msg,
                priority="low",
                tags="heartbeat,bridge",
                url=NTFY_PUSH_URL,
            )

            log.info(
                "Heartbeat: Supabase=%s ntfy=%s battery=%s%% net=%s storage=%s",
                "OK" if sb_ok else "FAIL",
                "OK" if ntfy_ok else "FAIL",
                battery_level,
                network,
                use_pct,
            )
        except Exception:
            log.error("Heartbeat loop unhandled exception:\n%s", traceback.format_exc())

        time.sleep(HEARTBEAT_INTERVAL)


# =============================================================================
# CLOUDFLARED WATCHDOG
# =============================================================================

def is_cloudflared_running() -> bool:
    """Return True if a cloudflared process is alive."""
    try:
        result = subprocess.run(
            ["pgrep", "-f", "cloudflared"],
            capture_output=True, text=True, timeout=8
        )
        return result.returncode == 0 and bool(result.stdout.strip())
    except Exception as e:
        log.warning("is_cloudflared_running check error: %s", e)
        return False


def restart_cloudflared() -> bool:
    """Restart cloudflared tunnel as a detached background process."""
    global _cloudflared_restart_count
    cmd = f"cloudflared tunnel run {CLOUDFLARED_UUID}"
    log.warning("Restarting cloudflared: %s", cmd)
    try:
        subprocess.Popen(
            cmd,
            shell=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        _cloudflared_restart_count += 1
        log.info("cloudflared restart #%d issued.", _cloudflared_restart_count)
        return True
    except Exception as e:
        log.error("Failed to restart cloudflared: %s", e)
        return False


def cloudflared_watchdog_loop() -> None:
    """Background thread: ensure cloudflared stays alive, alert + restart if dead."""
    log.info("Cloudflared watchdog started. UUID: %s", CLOUDFLARED_UUID)
    # Short grace period to allow cloudflared to start via pm2 first
    time.sleep(30)
    while True:
        try:
            if not is_cloudflared_running():
                log.error("cloudflared is NOT running \u2014 attempting restart!")
                restarted = restart_cloudflared()
                send_ntfy(
                    title="\U0001f6a8 cloudflared DOWN",
                    message=(
                        f"cloudflared was not running on {DEVICE_ID}.\n"
                        f"Restart attempted: {'YES' if restarted else 'NO'}\n"
                        f"Total restarts: {_cloudflared_restart_count}\n"
                        f"Bridge v{VERSION}"
                    ),
                    priority="urgent",
                    tags="rotating_light,cloud",
                )
            else:
                log.debug("cloudflared OK")
        except Exception:
            log.error(
                "cloudflared watchdog unhandled:\n%s", traceback.format_exc()
            )

        time.sleep(CLOUDFLARED_CHECK_INTERVAL)


# =============================================================================
# TUNNEL HEALTH MONITOR
# =============================================================================

def tunnel_check_loop() -> None:
    """Background thread: check public URL health, alert if repeatedly down."""
    fail_count = 0
    alerted = False
    log.info("Tunnel health monitor started. URL: %s", PUBLIC_URL)
    while True:
        try:
            req = Request(PUBLIC_URL, method="GET")
            with urlopen(req, timeout=15) as resp:
                if resp.status == 200:
                    if fail_count > 0:
                        log.info(
                            "Tunnel recovered after %d failure(s).", fail_count
                        )
                        if alerted:
                            send_ntfy(
                                title="\u2705 BRIDGE TUNNEL RECOVERED",
                                message=(
                                    f"Tunnel back online after {fail_count} consecutive failures.\n"
                                    f"URL: {PUBLIC_URL}\nBridge v{VERSION}"
                                ),
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
            log.warning(
                "Tunnel check failed (%d/%d): %s",
                fail_count,
                TUNNEL_FAIL_THRESHOLD,
                e,
            )
            if fail_count >= TUNNEL_FAIL_THRESHOLD and not alerted:
                log.error("Tunnel DEAD \u2014 sending urgent alert!")
                send_ntfy(
                    title="\U0001f6a8 BRIDGE TUNNEL DOWN",
                    message=(
                        f"Public URL failed {fail_count} consecutive checks.\n"
                        f"URL: {PUBLIC_URL}\nError: {e}\nBridge v{VERSION}"
                    ),
                    priority="urgent",
                    tags="rotating_light,skull",
                )
                alerted = True

        time.sleep(TUNNEL_CHECK_INTERVAL)


# =============================================================================
# HTTP REQUEST HANDLER
# =============================================================================

class BridgeHandler(BaseHTTPRequestHandler):
    """HTTP request handler for all bridge endpoints."""

    def log_message(self, fmt, *args):
        # Redirect BaseHTTPRequestHandler logs to our logger
        log.info("HTTP %s", fmt % args)

    def send_json(self, data: dict, status: int = 200) -> None:
        """Serialize dict to JSON and write HTTP response."""
        body = json.dumps(data, ensure_ascii=False, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def send_error_json(self, message: str, status: int = 400) -> None:
        """Send a JSON error response."""
        self.send_json({"success": False, "error": message}, status)

    def read_body_json(self) -> dict:
        """Read and parse JSON request body."""
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return {}
        raw = self.rfile.read(length)
        return json.loads(raw.decode("utf-8"))

    def do_OPTIONS(self):
        """Handle CORS preflight."""
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        """Route all GET requests."""
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        params = parse_qs(parsed.query)

        try:
            if path in ("/health", "/", ""):
                # Primary health endpoint - fast, lightweight
                self.send_json(check_health())

            elif path == "/status":
                # Full device state dump
                self.send_json(build_full_state())

            elif path == "/battery":
                self.send_json(get_battery())

            elif path == "/apps":
                self.send_json({"apps": get_installed_apps()})

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
                threading.Thread(
                    target=termux_speak, args=(msg,), daemon=True
                ).start()
                self.send_json({"success": True, "msg": msg})

            elif path == "/vibrate":
                try:
                    duration = int(params.get("duration", ["500"])[0])
                except ValueError:
                    duration = 500
                termux_vibrate(duration)
                self.send_json({"success": True, "duration": duration})

            elif path == "/listen":
                try:
                    timeout = int(params.get("timeout", ["10"])[0])
                except ValueError:
                    timeout = 10
                self.send_json(termux_listen(timeout))

            else:
                self.send_error_json(f"Unknown endpoint: {path}", 404)

        except Exception:
            tb = traceback.format_exc()
            log.error("GET %s unhandled:\n%s", path, tb)
            self.send_error_json("Internal server error", 500)

    def do_POST(self):
        """Route all POST requests."""
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
                self.send_json(run_exec(command))

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
                threading.Thread(
                    target=termux_speak, args=(msg,), daemon=True
                ).start()
                self.send_json({"success": True, "msg": msg})

            elif path == "/vibrate":
                try:
                    duration = int(body.get("duration", 500))
                except (ValueError, TypeError):
                    duration = 500
                termux_vibrate(duration)
                self.send_json({"success": True, "duration": duration})

            elif path == "/write_file":
                file_path = body.get("path", "")
                content = body.get("content", "")
                if not file_path:
                    self.send_error_json("Missing 'path' field")
                    return
                self.send_json(write_file(file_path, content))

            elif path == "/listen":
                try:
                    timeout = int(body.get("timeout", 10))
                except (ValueError, TypeError):
                    timeout = 10
                self.send_json(termux_listen(timeout))

            elif path == "/conversation":
                msg = body.get("msg", "")
                if not msg:
                    self.send_error_json("Missing 'msg' field")
                    return
                threading.Thread(
                    target=termux_speak, args=(msg,), daemon=True
                ).start()
                termux_toast(msg)
                self.send_json({"success": True, "action": "conversation", "msg": msg})

            elif path == "/voice":
                msg = body.get("msg", "")
                if not msg:
                    self.send_error_json("Missing 'msg' field")
                    return
                termux_vibrate(200)
                threading.Thread(
                    target=termux_speak, args=(msg,), daemon=True
                ).start()
                self.send_json({"success": True, "action": "voice", "msg": msg})

            elif path == "/ntfy":
                title = body.get("title", "Bridge Notification")
                message = body.get("message", "")
                if not message:
                    self.send_error_json("Missing 'message' field")
                    return
                priority = body.get("priority", "default")
                tags = body.get("tags", "bridge")
                ok = send_ntfy(
                    title=title, message=message, priority=priority, tags=tags
                )
                self.send_json({"success": ok})

            elif path == "/push_state":
                # Manual trigger: push state to Supabase + ntfy
                state = build_full_state()
                sb_ok = push_to_supabase(state)
                meta = state.get("metadata", {})
                ntfy_ok = send_ntfy(
                    title=f"\U0001f4e1 Manual Push \u2014 {DEVICE_ID}",
                    message=(
                        f"Manual state push requested.\n"
                        f"Battery: {meta.get('battery_level')}%\n"
                        f"Network: {meta.get('network')}\n"
                        f"Bridge v{VERSION}"
                    ),
                    priority="default",
                    tags="bridge",
                    url=NTFY_PUSH_URL,
                )
                self.send_json(
                    {"success": sb_ok or ntfy_ok, "supabase": sb_ok, "ntfy": ntfy_ok}
                )

            elif path in ("/health", "/"):
                self.send_json(check_health())

            else:
                self.send_error_json(f"Unknown endpoint: {path}", 404)

        except Exception:
            tb = traceback.format_exc()
            log.error("POST %s unhandled:\n%s", path, tb)
            self.send_error_json("Internal server error", 500)


# =============================================================================
# SERVER STARTUP
# =============================================================================

def start_background_threads() -> None:
    """Launch all background daemon threads."""
    threads = [
        threading.Thread(
            target=heartbeat_loop, daemon=True, name="Heartbeat"
        ),
        threading.Thread(
            target=cloudflared_watchdog_loop,
            daemon=True,
            name="CloudflaredWatchdog",
        ),
        threading.Thread(
            target=tunnel_check_loop, daemon=True, name="TunnelCheck"
        ),
    ]
    for t in threads:
        t.start()
        log.info("Thread started: %s", t.name)


def start_server() -> None:
    """Bind HTTP server with port fallback, then serve forever."""
    port = BASE_PORT
    server = None

    # Try BASE_PORT, BASE_PORT+1, BASE_PORT+2 before giving up
    for attempt in range(3):
        try:
            server = HTTPServer(("0.0.0.0", port), BridgeHandler)
            log.info("Bridge v%s bound to port %d", VERSION, port)
            break
        except OSError as e:
            if attempt < 2:
                log.warning(
                    "Port %d unavailable (%s). Trying %d ...", port, e, port + 1
                )
                port += 1
            else:
                log.critical("Could not bind to any port. Aborting.")
                sys.exit(1)

    # Announce startup
    send_ntfy(
        title=f"\U0001f7e2 Bridge v{VERSION}: Online and Bulletproof",
        message=(
            f"Bridge v{VERSION} started on {DEVICE_ID}.\n"
            f"HTTP server: port {port}\n"
            f"Supabase: {SUPABASE_URL}\n"
            f"Heartbeat interval: {HEARTBEAT_INTERVAL}s\n"
            f"Cloudflared UUID: {CLOUDFLARED_UUID}\n"
            f"Started at: {datetime.utcnow().isoformat()} UTC"
        ),
        priority="high",
        tags="rocket,bridge,white_check_mark",
    )

    start_background_threads()

    log.info("=" * 60)
    log.info("TCC Bridge v%s \u2014 Online and Bulletproof", VERSION)
    log.info("Device  : %s", DEVICE_ID)
    log.info("Port    : %d", port)
    log.info("Supabase: %s", SUPABASE_URL)
    log.info("ntfy    : %s", NTFY_BRIDGE_URL)
    log.info("Tunnel  : %s", PUBLIC_URL)
    log.info("Log     : %s", log_path)
    log.info("=" * 60)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        log.info("Shutdown requested via KeyboardInterrupt.")
    except Exception:
        log.critical("Server crashed:\n%s", traceback.format_exc())
    finally:
        if server:
            server.shutdown()
        log.info("Bridge stopped.")


# =============================================================================
# CLI ENTRY POINT
# =============================================================================

def main() -> None:
    """Parse CLI arguments or start the server."""
    if len(sys.argv) > 1:
        arg = sys.argv[1]

        if arg == "--once":
            log.info("--once: pushing state then exiting.")
            state = build_full_state()
            sb_ok = push_to_supabase(state)
            meta = state.get("metadata", {})
            ntfy_ok = send_ntfy(
                title=f"\U0001f4e1 One-Shot Push \u2014 {DEVICE_ID}",
                message=(
                    f"Battery: {meta.get('battery_level')}%\n"
                    f"Network: {meta.get('network')}\n"
                    f"Bridge v{VERSION}"
                ),
                priority="default",
                tags="bridge",
                url=NTFY_PUSH_URL,
            )
            log.info("Supabase=%s ntfy=%s", sb_ok, ntfy_ok)
            sys.exit(0 if (sb_ok or ntfy_ok) else 1)

        elif arg == "--status":
            print(json.dumps(build_full_state(), indent=2, default=str))
            sys.exit(0)

        elif arg == "--health":
            print(json.dumps(check_health(), indent=2, default=str))
            sys.exit(0)

        elif arg == "--apps":
            print(json.dumps(get_installed_apps(), indent=2))
            sys.exit(0)

        elif arg == "--battery":
            print(json.dumps(get_battery(), indent=2))
            sys.exit(0)

        elif arg == "--ntfy-only":
            state = build_full_state()
            meta = state.get("metadata", {})
            ok = send_ntfy(
                title=f"\U0001f4e1 ntfy-only \u2014 {DEVICE_ID}",
                message=(
                    f"Battery: {meta.get('battery_level')}%\n"
                    f"Network: {meta.get('network')}\n"
                    f"Bridge v{VERSION}"
                ),
                priority="default",
                tags="bridge",
                url=NTFY_PUSH_URL,
            )
            sys.exit(0 if ok else 1)

        elif arg == "--help":
            print(f"bridge.py v{VERSION} \u2014 TCC Master Bridge")
            print("Usage:")
            print("  python bridge.py             # Start HTTP server + background loops")
            print("  python bridge.py --once      # Push state once then exit")
            print("  python bridge.py --status    # Print full device state JSON")
            print("  python bridge.py --health    # Print health check JSON")
            print("  python bridge.py --apps      # Print installed apps JSON")
            print("  python bridge.py --battery   # Print battery JSON")
            print("  python bridge.py --ntfy-only # Push ntfy notification only")
            sys.exit(0)

        else:
            print(f"Unknown argument: {arg}. Use --help for usage.")
            sys.exit(1)
    else:
        start_server()


if __name__ == "__main__":
    main()
