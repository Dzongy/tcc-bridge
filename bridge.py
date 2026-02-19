#!/usr/bin/env python3
"""
bridge.py v5.3.0 â BULLETPROOF UNIFIED EDITION
Merges HTTP server (v5.2.0) + push-based state reporting (v2.0.0)
Kael God Builder / TCC / ZENITH

Endpoints:
  GET  /health      â JSON status, uptime, last_push, device
  GET  /            â bridge online banner
  GET  /battery     â battery info
  GET  /toast       â termux toast (?msg=)
  GET  /speak       â termux TTS (?msg=)
  GET  /vibrate     â termux vibrate (?duration=)
  GET  /listen      â microphone record (?timeout=)
  POST /exec        â run shell command
  POST /toast       â termux toast
  POST /speak       â termux TTS
  POST /vibrate     â termux vibrate
  POST /write_file  â write file to device
  POST /read_file   â read file from device
  POST /listen      â microphone record
  POST /conversationâ speak + toast
  POST /voice       â vibrate + speak
  POST /health      â same as GET /health

Background threads:
  - StateReporter: pushes device state to Supabase + ntfy every 5 min
  - TunnelCheck: monitors public URL, alerts via ntfy on failure
"""

import json
import logging
import os
import subprocess
import sys
import threading
import time
import traceback
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Dict, List, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlparse
from urllib.request import Request, urlopen

# ââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
# LOGGING
# ââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
LOG_FILE = os.path.expanduser("~/bridge.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
    ],
)
log = logging.getLogger("bridge")

# ââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
# CONFIG
# ââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
VERSION = "5.3.0"
DEVICE_ID = os.environ.get("BRIDGE_DEVICE_ID", "amos-arms")
BASE_PORT = int(os.environ.get("BRIDGE_PORT", 8080))
BRIDGE_AUTH = os.environ.get("BRIDGE_AUTH", "amos-bridge-2026")

# Supabase
SUPABASE_URL = os.environ.get(
    "SUPABASE_URL", "https://vbqbbziqleymxcyesmky.supabase.co"
)
SUPABASE_KEY = os.environ.get(
    "SUPABASE_KEY", "sb_secret_lIbl-DBgdnrt_fejgJjKqg_qR62SVEm"
)

# ntfy
NTFY_STATE_TOPIC = os.environ.get("NTFY_STATE_TOPIC", "zenith-escape")
NTFY_ALERT_URL = os.environ.get("NTFY_ALERT_URL", "https://ntfy.sh/tcc-zenith-hive")
NTFY_BASE = "https://ntfy.sh"

# Tunnel / public health check
PUBLIC_URL = os.environ.get(
    "BRIDGE_PUBLIC_URL", "https://zenith.cosmic-claw.com/health"
)
TUNNEL_CHECK_INTERVAL = int(os.environ.get("TUNNEL_CHECK_INTERVAL", 120))
TUNNEL_FAIL_THRESHOLD = int(os.environ.get("TUNNEL_FAIL_THRESHOLD", 3))

# Push interval (seconds)
STATE_PUSH_INTERVAL = int(os.environ.get("STATE_PUSH_INTERVAL", 300))  # 5 min

# Startup timestamp
START_TIME = time.time()

# Shared state (thread-safe via lock)
_state_lock = threading.Lock()
_last_push_time: Optional[float] = None
_last_push_status: str = "never"


def _set_last_push(status: str) -> None:
    global _last_push_time, _last_push_status
    with _state_lock:
        _last_push_time = time.time()
        _last_push_status = status


def _get_last_push() -> Dict[str, Any]:
    with _state_lock:
        return {
            "time": _last_push_time,
            "iso": (
                datetime.fromtimestamp(_last_push_time, tz=timezone.utc).isoformat()
                if _last_push_time
                else None
            ),
            "status": _last_push_status,
        }


# ââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
# GENERAL HELPERS
# ââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ

def get_uptime() -> float:
    return round(time.time() - START_TIME, 2)


def run_shell(cmd: str, timeout: int = 30) -> str:
    """Run shell command, return stdout or stderr or error string."""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=timeout
        )
        return result.stdout.strip() or result.stderr.strip() or ""
    except subprocess.TimeoutExpired:
        return "error: timeout"
    except Exception as e:
        return f"error: {e}"


# ââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
# DEVICE STATE COLLECTORS
# ââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ

def get_battery() -> Dict[str, Any]:
    """Battery via termux-battery-status, fallback to dumpsys."""
    try:
        result = subprocess.run(
            ["termux-battery-status"],
            capture_output=True, text=True, timeout=10
        )
        data = json.loads(result.stdout)
        return {
            "percentage": data.get("percentage", -1),
            "plugged": data.get("plugged", "UNKNOWN"),
            "status": data.get("status", "UNKNOWN"),
            "temperature": data.get("temperature", -1),
            "source": "termux",
        }
    except Exception:
        pass

    # Fallback: dumpsys battery
    try:
        raw = run_shell("dumpsys battery", timeout=10)
        info: Dict[str, Any] = {"source": "dumpsys"}
        for line in raw.splitlines():
            line = line.strip()
            if "level:" in line:
                try:
                    info["percentage"] = int(line.split(":", 1)[1].strip())
                except ValueError:
                    pass
            elif "status:" in line:
                info["status"] = line.split(":", 1)[1].strip()
            elif "plugged:" in line:
                info["plugged"] = line.split(":", 1)[1].strip()
            elif "temperature:" in line:
                try:
                    info["temperature"] = int(line.split(":", 1)[1].strip()) / 10.0
                except ValueError:
                    pass
        info.setdefault("percentage", -1)
        info.setdefault("status", "UNKNOWN")
        info.setdefault("plugged", "UNKNOWN")
        return info
    except Exception as e:
        log.warning("get_battery fallback failed: %s", e)
        return {"percentage": -1, "plugged": "UNKNOWN", "status": "UNKNOWN", "source": "error"}


def get_uptime_str() -> str:
    """System uptime from /proc/uptime."""
    try:
        with open("/proc/uptime") as f:
            secs = float(f.read().split()[0])
        h = int(secs // 3600)
        m = int((secs % 3600) // 60)
        s = int(secs % 60)
        return f"{h}h {m}m {s}s"
    except Exception:
        return run_shell("uptime -p", timeout=5) or "unknown"


def get_memory() -> Dict[str, Any]:
    """Memory info from /proc/meminfo."""
    try:
        mem: Dict[str, int] = {}
        with open("/proc/meminfo") as f:
            for line in f:
                parts = line.split()
                if len(parts) >= 2:
                    key = parts[0].rstrip(":")
                    val = int(parts[1])  # kB
                    mem[key] = val
        total_mb = mem.get("MemTotal", 0) // 1024
        free_mb = mem.get("MemAvailable", mem.get("MemFree", 0)) // 1024
        used_mb = total_mb - free_mb
        return {
            "total_mb": total_mb,
            "used_mb": used_mb,
            "free_mb": free_mb,
            "use_percent": (
                round(used_mb / total_mb * 100, 1) if total_mb > 0 else 0
            ),
        }
    except Exception as e:
        log.warning("get_memory failed: %s", e)
        return {}


def get_storage() -> Dict[str, Any]:
    """Storage info for /data via df."""
    try:
        raw = run_shell("df -h /data", timeout=10)
        lines = raw.splitlines()
        if len(lines) >= 2:
            parts = lines[-1].split()
            if len(parts) >= 5:
                return {
                    "size": parts[1],
                    "used": parts[2],
                    "available": parts[3],
                    "use_percent": parts[4],
                    "mount": parts[5] if len(parts) > 5 else "/data",
                }
    except Exception as e:
        log.warning("get_storage failed: %s", e)
    return {}


def get_current_activity() -> str:
    """Best-effort: get foreground app package/activity."""
    cmds = [
        "dumpsys activity activities | grep -E 'mResumedActivity|ResumedActivity' | head -1",
        "dumpsys window windows | grep -E 'mCurrentFocus|mFocusedApp' | head -1",
        "dumpsys activity | grep 'top-activity' | head -1",
    ]
    for cmd in cmds:
        result = run_shell(cmd, timeout=10)
        if result and "error" not in result.lower():
            return result.strip()
    return "unknown"


def get_installed_apps(limit: int = 150) -> List[str]:
    """List installed packages via pm."""
    try:
        raw = run_shell("pm list packages", timeout=20)
        apps = []
        for line in raw.splitlines():
            if line.startswith("package:"):
                apps.append(line[len("package:"):])
        return apps[:limit]
    except Exception as e:
        log.warning("get_installed_apps failed: %s", e)
        return []


def get_device_meta() -> Dict[str, Any]:
    """Static device metadata."""
    return {
        "model": run_shell("getprop ro.product.model", timeout=5),
        "android_version": run_shell("getprop ro.build.version.release", timeout=5),
        "hostname": run_shell("hostname", timeout=5),
        "arch": run_shell("uname -m", timeout=5),
        "kernel": run_shell("uname -r", timeout=5),
    }


# ââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
# TERMUX ACTIONS
# ââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ

def termux_toast(msg: str) -> None:
    try:
        subprocess.run(["termux-toast", "-s", str(msg)], timeout=10, check=False)
    except Exception as e:
        log.warning("termux_toast error: %s", e)


def termux_speak(msg: str) -> None:
    try:
        subprocess.run(["termux-tts-speak", str(msg)], timeout=60, check=False)
    except Exception as e:
        log.warning("termux_speak error: %s", e)


def termux_vibrate(duration: int = 500) -> None:
    try:
        subprocess.run(
            ["termux-vibrate", "-d", str(duration)], timeout=10, check=False
        )
    except Exception as e:
        log.warning("termux_vibrate error: %s", e)


def termux_listen(timeout: int = 10) -> Dict[str, Any]:
    try:
        path = os.path.expanduser("~/bridge_listen.mp4")
        subprocess.run(
            ["termux-microphone-record", "-l", str(timeout), "-f", path],
            timeout=timeout + 10,
            check=False,
        )
        return {"success": True, "file": path}
    except Exception as e:
        log.error("termux_listen error: %s", e)
        return {"success": False, "error": str(e)}


def write_file(path: str, content: str) -> Dict[str, Any]:
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


def read_file(path: str) -> Dict[str, Any]:
    try:
        expanded = os.path.expanduser(path)
        with open(expanded, "r", encoding="utf-8") as f:
            content = f.read()
        return {"success": True, "path": expanded, "content": content}
    except FileNotFoundError:
        return {"success": False, "error": f"File not found: {path}"}
    except Exception as e:
        log.error("read_file error: %s", e)
        return {"success": False, "error": str(e)}


def run_exec(command: str) -> Dict[str, Any]:
    try:
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True, timeout=60
        )
        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
        }
    except subprocess.TimeoutExpired:
        return {"stdout": "", "stderr": "Command timed out (60s)", "returncode": -1}
    except Exception as e:
        log.error("run_exec error: %s", e)
        return {"stdout": "", "stderr": str(e), "returncode": -1}


# ââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
# NTFY HELPERS
# ââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ

def _ntfy_post(
    url: str,
    message: str,
    title: str = "",
    priority: str = "default",
    tags: str = "",
    timeout: int = 12,
) -> bool:
    """Low-level ntfy POST with retry (2 attempts)."""
    headers = {"Content-Type": "text/plain; charset=utf-8"}
    if title:
        headers["Title"] = title
    if priority:
        headers["Priority"] = priority
    if tags:
        headers["Tags"] = tags

    for attempt in range(1, 3):
        try:
            req = Request(
                url,
                data=message.encode("utf-8"),
                headers=headers,
                method="POST",
            )
            with urlopen(req, timeout=timeout) as resp:
                if resp.status in (200, 201):
                    return True
                log.warning("ntfy HTTP %s (attempt %d)", resp.status, attempt)
        except Exception as e:
            log.warning("ntfy POST attempt %d failed: %s", attempt, e)
            if attempt < 2:
                time.sleep(3)
    return False


def send_alert_ntfy(
    title: str,
    message: str,
    priority: str = "high",
    tags: str = "warning",
) -> bool:
    return _ntfy_post(
        NTFY_ALERT_URL,
        message,
        title=title,
        priority=priority,
        tags=tags,
    )


def send_state_ntfy(state: Dict[str, Any]) -> bool:
    """Push a human-readable state summary to the state ntfy topic."""
    bat = state.get("battery", {})
    storage = state.get("storage", {})
    memory = state.get("memory", {})
    network = state.get("network", "unknown")
    now_str = datetime.now().strftime("%H:%M")

    pct = bat.get("percentage", "?")
    bat_status = bat.get("status", "?")
    plugged = bat.get("plugged", "?")
    mem_used = memory.get("used_mb", "?")
    mem_total = memory.get("total_mb", "?")
    mem_pct = memory.get("use_percent", "?")
    stor_used = storage.get("used", "?")
    stor_total = storage.get("size", "?")
    stor_pct = storage.get("use_percent", "?")

    lines = [
        f"Device : {DEVICE_ID}",
        f"Bridge : v{VERSION}",
        f"Battery: {pct}% [{bat_status}] plugged={plugged}",
        f"Memory : {mem_used}/{mem_total} MB ({mem_pct}%)",
        f"Storage: {stor_used}/{stor_total} ({stor_pct})",
        f"Network: {network}",
        f"Uptime : {state.get('system_uptime', '?')}",
        f"Apps   : {len(state.get('apps', []))}",
    ]
    msg = "\n".join(lines)
    url = f"{NTFY_BASE}/{NTFY_STATE_TOPIC}"
    return _ntfy_post(
        url,
        msg,
        title=f"TCC Heartbeat â {now_str}",
        priority="low",
        tags="bridge,heartbeat,amos-arms",
    )


# ââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
# SUPABASE PUSH
# ââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ

def _supabase_headers() -> Dict[str, str]:
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates",  # upsert
    }


def push_to_supabase(payload: Dict[str, Any]) -> bool:
    """Upsert device state into Supabase device_state table."""
    endpoint = f"{SUPABASE_URL}/rest/v1/device_state"
    body = json.dumps(payload, default=str).encode("utf-8")
    headers = _supabase_headers()
    headers["Content-Length"] = str(len(body))

    for attempt in range(1, 4):  # 3 attempts
        try:
            req = Request(endpoint, data=body, headers=headers, method="POST")
            with urlopen(req, timeout=15) as resp:
                if resp.status in (200, 201):
                    log.info("[Supabase] State pushed OK (attempt %d)", attempt)
                    return True
                log.warning(
                    "[Supabase] HTTP %s on attempt %d", resp.status, attempt
                )
        except HTTPError as e:
            log.warning("[Supabase] HTTPError %s on attempt %d: %s", e.code, attempt, e)
        except URLError as e:
            log.warning("[Supabase] URLError on attempt %d: %s", attempt, e)
        except Exception as e:
            log.warning("[Supabase] Error on attempt %d: %s", attempt, e)

        if attempt < 3:
            backoff = attempt * 5
            log.info("[Supabase] Retrying in %ds ...", backoff)
            time.sleep(backoff)

    log.error("[Supabase] All push attempts failed.")
    return False


# ââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
# STATE REPORTER THREAD
# ââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ

def _collect_state() -> Dict[str, Any]:
    """Gather full device state snapshot."""
    bat = get_battery()
    mem = get_memory()
    stor = get_storage()
    sys_uptime = get_uptime_str()
    activity = get_current_activity()
    apps = get_installed_apps()
    meta = get_device_meta()
    network = _get_network_info()

    return {
        "device_id": DEVICE_ID,
        "bridge_version": VERSION,
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        "bridge_uptime_sec": get_uptime(),
        "system_uptime": sys_uptime,
        "battery": bat,
        "memory": mem,
        "storage": stor,
        "network": network,
        "current_activity": activity,
        "apps": apps,
        "apps_count": len(apps),
        "device_meta": meta,
    }


def _get_network_info() -> str:
    """Best-effort network detection."""
    try:
        # Try termux-wifi-connectioninfo first
        r = subprocess.run(
            ["termux-wifi-connectioninfo"],
            capture_output=True, text=True, timeout=8
        )
        if r.returncode == 0 and r.stdout.strip():
            data = json.loads(r.stdout)
            ssid = data.get("ssid", "")
            if ssid and ssid not in ("", "<unknown ssid>"):
                return f"wifi:{ssid}"
    except Exception:
        pass

    # Fallback dumpsys
    wifi_raw = run_shell(
        "dumpsys wifi | grep 'Wi-Fi is' | head -1", timeout=10
    )
    if "enabled" in wifi_raw.lower():
        ssid_raw = run_shell(
            "dumpsys wifi | grep 'SSID:' | head -1", timeout=10
        )
        ssid = ssid_raw.split(":", 1)[-1].strip() if ":" in ssid_raw else "unknown"
        return f"wifi:{ssid}"

    mobile_raw = run_shell(
        "dumpsys telephony.registry | grep 'mDataConnectionState' | head -1",
        timeout=10,
    )
    if "2" in mobile_raw:
        return "mobile:data"

    return "offline"


def state_reporter_loop() -> None:
    """Background thread: collect + push state every STATE_PUSH_INTERVAL seconds."""
    log.info(
        "[StateReporter] Started. Push interval=%ds, Supabase=%s, ntfy topic=%s",
        STATE_PUSH_INTERVAL, SUPABASE_URL, NTFY_STATE_TOPIC,
    )

    # Initial push shortly after startup
    time.sleep(10)

    while True:
        try:
            log.info("[StateReporter] Collecting device state ...")
            state = _collect_state()

            supabase_ok = False
            ntfy_ok = False

            try:
                supabase_ok = push_to_supabase(state)
            except Exception as e:
                log.error("[StateReporter] Supabase push exception: %s", e)

            try:
                ntfy_ok = send_state_ntfy(state)
            except Exception as e:
                log.error("[StateReporter] ntfy push exception: %s", e)

            status = "ok" if (supabase_ok and ntfy_ok) else (
                "partial" if (supabase_ok or ntfy_ok) else "failed"
            )
            _set_last_push(status)
            log.info(
                "[StateReporter] Push done â supabase=%s ntfy=%s status=%s",
                supabase_ok, ntfy_ok, status,
            )
        except Exception:
            tb = traceback.format_exc()
            log.error("[StateReporter] Unhandled exception:\n%s", tb)
            _set_last_push("error")

        time.sleep(STATE_PUSH_INTERVAL)


# ââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
# TUNNEL CHECK THREAD
# ââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ

def tunnel_check_loop() -> None:
    fail_count = 0
    alerted = False
    log.info("[TunnelCheck] Started. Monitoring: %s", PUBLIC_URL)

    while True:
        try:
            req = Request(PUBLIC_URL, method="GET")
            req.add_header("User-Agent", f"bridge/{VERSION}")
            with urlopen(req, timeout=15) as resp:
                if resp.status == 200:
                    if fail_count > 0:
                        log.info(
                            "[TunnelCheck] Tunnel recovered after %d failure(s).",
                            fail_count,
                        )
                        if alerted:
                            send_alert_ntfy(
                                "\u2705 BRIDGE TUNNEL RECOVERED",
                                f"Public URL is back online after {fail_count} consecutive failure(s).\nURL: {PUBLIC_URL}",
                                priority="default",
                                tags="white_check_mark",
                            )
                    fail_count = 0
                    alerted = False
                else:
                    raise URLError(f"HTTP {resp.status}")
        except Exception as e:
            fail_count += 1
            log.warning(
                "[TunnelCheck] Fail %d/%d: %s", fail_count, TUNNEL_FAIL_THRESHOLD, e
            )
            if fail_count >= TUNNEL_FAIL_THRESHOLD and not alerted:
                log.error("[TunnelCheck] Tunnel DEAD â alerting via ntfy!")
                send_alert_ntfy(
                    "\U0001f6a8 BRIDGE TUNNEL DOWN",
                    f"Public URL has failed {fail_count} consecutive health checks.\n"
                    f"URL: {PUBLIC_URL}\nError: {e}\nBridge v{VERSION}",
                    priority="urgent",
                    tags="rotating_light,skull",
                )
                alerted = True

        time.sleep(TUNNEL_CHECK_INTERVAL)


# ââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
# AUTH HELPER
# ââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ

def _check_auth(handler: "BridgeHandler") -> bool:
    """Return True if request is authorised (or if BRIDGE_AUTH is empty).
    Checks Bearer token in Authorization header.
    """
    if not BRIDGE_AUTH:
        return True  # Auth disabled
    auth_header = handler.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[len("Bearer "):].strip()
        if token == BRIDGE_AUTH:
            return True
    # Also check X-Bridge-Token header for convenience
    token2 = handler.headers.get("X-Bridge-Token", "")
    if token2 == BRIDGE_AUTH:
        return True
    return False


# ââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
# HTTP HANDLER
# ââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ

class BridgeHandler(BaseHTTPRequestHandler):

    def log_message(self, fmt, *args):  # noqa: N802
        log.info("HTTP %s", fmt % args)

    # ââ helpers ââââââââââââââââââââââââââââââââââââââââââââââââ

    def send_json(self, data: Dict[str, Any], status: int = 200) -> None:
        body = json.dumps(data, ensure_ascii=False, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def send_error_json(self, message: str, status: int = 400) -> None:
        self.send_json({"success": False, "error": message}, status)

    def read_body_json(self) -> Dict[str, Any]:
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return {}
        raw = self.rfile.read(length)
        if not raw:
            return {}
        return json.loads(raw.decode("utf-8"))

    def require_auth(self) -> bool:
        """Returns True if authorised, else sends 401 and returns False."""
        if not _check_auth(self):
            self.send_json(
                {"success": False, "error": "Unauthorized"},
                status=401,
            )
            return False
        return True

    # ââ GET ââââââââââââââââââââââââââââââââââââââââââââââââââââ

    def do_GET(self):  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        params = parse_qs(parsed.query)

        try:
            if path == "/health":
                # Health is public â no auth required
                bat = get_battery()
                lp = _get_last_push()
                self.send_json({
                    "status": "ok",
                    "version": VERSION,
                    "device": DEVICE_ID,
                    "uptime": get_uptime(),
                    "last_push": lp.get("iso"),
                    "last_push_status": lp.get("status"),
                    "battery": bat.get("percentage", -1),
                    "battery_status": bat.get("status", "UNKNOWN"),
                    "plugged": bat.get("plugged", "UNKNOWN"),
                    "bridge_alive": True,
                })
                return

            if path == "/":
                self.send_json({
                    "bridge": "online",
                    "version": VERSION,
                    "device": DEVICE_ID,
                })
                return

            # Auth-required endpoints below
            if not self.require_auth():
                return

            if path == "/battery":
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
                threading.Thread(
                    target=termux_speak, args=(msg,), daemon=True
                ).start()
                self.send_json({"success": True, "msg": msg})

            elif path == "/vibrate":
                duration = int(params.get("duration", ["500"])[0])
                termux_vibrate(duration)
                self.send_json({"success": True, "duration": duration})

            elif path == "/listen":
                timeout = int(params.get("timeout", ["10"])[0])
                result = termux_listen(timeout)
                self.send_json(result)

            elif path == "/state":
                # Return current device state snapshot on demand
                state = _collect_state()
                self.send_json(state)

            else:
                self.send_error_json(f"Unknown endpoint: {path}", 404)

        except Exception:
            tb = traceback.format_exc()
            log.error("GET %s unhandled:\n%s", path, tb)
            self.send_error_json("Internal server error", 500)

    # ââ POST âââââââââââââââââââââââââââââââââââââââââââââââââââ

    def do_POST(self):  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"

        try:
            body = self.read_body_json()
        except Exception as e:
            self.send_error_json(f"Invalid JSON body: {e}")
            return

        try:
            if path == "/health":
                # Health POST â public
                bat = get_battery()
                lp = _get_last_push()
                self.send_json({
                    "status": "ok",
                    "version": VERSION,
                    "device": DEVICE_ID,
                    "uptime": get_uptime(),
                    "last_push": lp.get("iso"),
                    "last_push_status": lp.get("status"),
                    "battery": bat.get("percentage", -1),
                    "battery_status": bat.get("status", "UNKNOWN"),
                    "plugged": bat.get("plugged", "UNKNOWN"),
                    "bridge_alive": True,
                })
                return

            # Auth-required endpoints below
            if not self.require_auth():
                return

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
                threading.Thread(
                    target=termux_speak, args=(msg,), daemon=True
                ).start()
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

            elif path == "/read_file":
                file_path = body.get("path", "")
                if not file_path:
                    self.send_error_json("Missing 'path' field")
                    return
                result = read_file(file_path)
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

            elif path == "/push_now":
                # Trigger an immediate state push out-of-band
                def _push():
                    try:
                        state = _collect_state()
                        sb = push_to_supabase(state)
                        nt = send_state_ntfy(state)
                        status = "ok" if (sb and nt) else ("partial" if (sb or nt) else "failed")
                        _set_last_push(status)
                    except Exception as exc:
                        log.error("[push_now] %s", exc)
                        _set_last_push("error")
                threading.Thread(target=_push, daemon=True, name="PushNow").start()
                self.send_json({"success": True, "action": "push_now", "note": "Push triggered in background"})

            elif path == "/state":
                state = _collect_state()
                self.send_json(state)

            else:
                self.send_error_json(f"Unknown endpoint: {path}", 404)

        except Exception:
            tb = traceback.format_exc()
            log.error("POST %s unhandled:\n%s", path, tb)
            self.send_error_json("Internal server error", 500)

    # ââ OPTIONS (CORS pre-flight) âââââââââââââââââââââââââââââââ

    def do_OPTIONS(self):  # noqa: N802
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header(
            "Access-Control-Allow-Headers",
            "Content-Type, Authorization, X-Bridge-Token",
        )
        self.end_headers()


# ââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
# SERVER STARTUP
# ââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ

def start_server() -> None:
    port = BASE_PORT
    server: Optional[HTTPServer] = None

    for attempt in range(3):
        try_port = port + attempt
        try:
            server = HTTPServer(("0.0.0.0", try_port), BridgeHandler)
            log.info("Bridge v%s listening on 0.0.0.0:%d", VERSION, try_port)
            break
        except OSError as e:
            log.warning("Port %d unavailable (%s)", try_port, e)
            if attempt == 2:
                log.critical("Could not bind to any port in range %d-%d. Aborting.", port, port + 2)
                sys.exit(1)

    assert server is not None

    # ââ Background threads ââââââââââââââââââââââââââââââââââââââ
    reporter = threading.Thread(
        target=state_reporter_loop,
        daemon=True,
        name="StateReporter",
    )
    reporter.start()

    tunnel_mon = threading.Thread(
        target=tunnel_check_loop,
        daemon=True,
        name="TunnelCheck",
    )
    tunnel_mon.start()

    # ââ Startup announcement ââââââââââââââââââââââââââââââââââââ
    log.info(
        "Bridge v%s UP | Device=%s | Auth=%s | StateInterval=%ds | TunnelCheck=%ds",
        VERSION,
        DEVICE_ID,
        "enabled" if BRIDGE_AUTH else "DISABLED",
        STATE_PUSH_INTERVAL,
        TUNNEL_CHECK_INTERVAL,
    )

    # Fire startup ntfy (non-blocking, best-effort)
    def _startup_notify():
        time.sleep(5)  # let everything settle first
        send_alert_ntfy(
            f"\U0001f7e2 Bridge v{VERSION} ONLINE â {DEVICE_ID}",
            f"Bridge v{VERSION} started.\nDevice: {DEVICE_ID}\nPush interval: {STATE_PUSH_INTERVAL}s",
            priority="default",
            tags="white_check_mark,bridge",
        )
    threading.Thread(target=_startup_notify, daemon=True, name="StartupNotify").start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        log.info("Shutdown requested (Ctrl-C).")
    finally:
        server.shutdown()
        log.info("Bridge v%s stopped.", VERSION)


# ââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
# CLI ENTRY POINT
# ââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ

def _cli() -> None:
    """Optional CLI commands for quick diagnostics."""
    if len(sys.argv) < 2:
        start_server()
        return

    cmd = sys.argv[1]

    if cmd == "--once":
        log.info("Running single state push ...")
        state = _collect_state()
        sb = push_to_supabase(state)
        nt = send_state_ntfy(state)
        log.info("Supabase=%s ntfy=%s", sb, nt)
        sys.exit(0 if (sb or nt) else 1)

    elif cmd == "--state":
        state = _collect_state()
        print(json.dumps(state, indent=2, default=str))

    elif cmd == "--apps":
        apps = get_installed_apps()
        print(json.dumps(apps, indent=2))

    elif cmd == "--battery":
        print(json.dumps(get_battery(), indent=2))

    elif cmd == "--health":
        bat = get_battery()
        lp = _get_last_push()
        print(json.dumps({
            "status": "ok",
            "version": VERSION,
            "device": DEVICE_ID,
            "uptime": get_uptime(),
            "last_push": lp.get("iso"),
            "battery": bat.get("percentage", -1),
            "bridge_alive": True,
        }, indent=2))

    elif cmd == "--help":
        print(
            f"bridge.py v{VERSION}\n"
            "Usage:\n"
            "  python bridge.py           â start HTTP server + background threads\n"
            "  python bridge.py --once    â push state once and exit\n"
            "  python bridge.py --state   â print state JSON and exit\n"
            "  python bridge.py --apps    â print installed apps and exit\n"
            "  python bridge.py --battery â print battery info and exit\n"
            "  python bridge.py --health  â print health JSON and exit\n"
            "\nEnvironment variables:\n"
            "  BRIDGE_PORT          HTTP port (default: 8080)\n"
            "  BRIDGE_AUTH          Auth token (default: amos-bridge-2026)\n"
            "  BRIDGE_DEVICE_ID     Device ID (default: amos-arms)\n"
            "  BRIDGE_PUBLIC_URL    Public URL for tunnel monitoring\n"
            "  SUPABASE_URL         Supabase REST URL\n"
            "  SUPABASE_KEY         Supabase API key\n"
            "  NTFY_STATE_TOPIC     ntfy topic for state heartbeats\n"
            "  NTFY_ALERT_URL       ntfy URL for alerts\n"
            "  STATE_PUSH_INTERVAL  Seconds between state pushes (default: 300)\n"
            "  TUNNEL_CHECK_INTERVAL Seconds between tunnel checks (default: 120)\n"
            "  TUNNEL_FAIL_THRESHOLD Failures before alert (default: 3)\n"
        )
    else:
        log.error("Unknown CLI argument: %s (use --help)", cmd)
        sys.exit(1)


if __name__ == "__main__":
    _cli()
