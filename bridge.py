#!/usr/bin/env python3
"""
Bulletproof Bridge V2 for Termux/Android
Author: Kael (Master Engineer)
Version: 2.0.0
"""

import os
import sys
import json
import time
import signal
import logging
import subprocess
import threading
import traceback
from datetime import datetime, timezone
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
from urllib.parse import urlparse, parse_qs
import urllib.request

# âââââââââââââââââââââââââââââââââââââââââââââ
# CONFIG
# âââââââââââââââââââââââââââââââââââââââââââââ
SUPABASE_URL  = "https://vbqbbziqleymxcyesmky.supabase.co"
SUPABASE_KEY  = "sb_secret_lIbl-DBgdnrt_fejgJjKqg_qR62SVEm"
NTFY_TOPIC    = "tcc-zenith-hive"
SERVER_PORT   = 8080
LOG_FILE      = os.path.expanduser("~/tcc-bridge-v2.log")
HEARTBEAT_IV  = 60   # seconds
MAX_LOG_LINES = 100

# âââââââââââââââââââââââââââââââââââââââââââââ
# LOGGING SETUP
# âââââââââââââââââââââââââââââââââââââââââââââ
log_formatter = logging.Formatter(
    "%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S"
)

file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
file_handler.setFormatter(log_formatter)

stream_handler = logging.StreamHandler(sys.stdout)
stream_handler.setFormatter(log_formatter)

logger = logging.getLogger("bridge_v2")
logger.setLevel(logging.DEBUG)
logger.addHandler(file_handler)
logger.addHandler(stream_handler)

# âââââââââââââââââââââââââââââââââââââââââââââ
# GLOBAL STATE
# âââââââââââââââââââââââââââââââââââââââââââââ
START_TIME = time.time()
_shutdown_flag = threading.Event()


# âââââââââââââââââââââââââââââââââââââââââââââ
# UTILITY HELPERS
# âââââââââââââââââââââââââââââââââââââââââââââ
def uptime_seconds():
    return round(time.time() - START_TIME, 2)


def safe_run(cmd, timeout=10):
    """Run a shell command safely, return (stdout, stderr, returncode)."""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return result.stdout.strip(), result.stderr.strip(), result.returncode
    except subprocess.TimeoutExpired:
        logger.warning(f"Command timed out: {cmd}")
        return "", "timeout", -1
    except Exception as e:
        logger.error(f"safe_run error for '{cmd}': {e}")
        return "", str(e), -1


def is_cloudflared_running():
    """Check if cloudflared is active via pgrep."""
    try:
        stdout, _, rc = safe_run("pgrep -x cloudflared", timeout=5)
        if rc == 0 and stdout:
            return True
        # Fallback: check by partial name
        stdout2, _, rc2 = safe_run("pgrep -f cloudflared", timeout=5)
        return rc2 == 0 and bool(stdout2)
    except Exception:
        return False


def get_network_status():
    """Return basic network connectivity info."""
    try:
        stdout, _, rc = safe_run("curl -s --max-time 5 -o /dev/null -w '%{http_code}' https://1.1.1.1", timeout=8)
        reachable = (rc == 0 and stdout == "200")
    except Exception:
        reachable = False
    try:
        ip_out, _, _ = safe_run("curl -s --max-time 5 https://api.ipify.org", timeout=8)
        public_ip = ip_out if ip_out else "unknown"
    except Exception:
        public_ip = "unknown"
    return {"internet_reachable": reachable, "public_ip": public_ip}


def get_device_status():
    """Collect device health metrics."""
    status = {}
    # Battery
    bat_out, _, _ = safe_run("termux-battery-status", timeout=8)
    try:
        status["battery"] = json.loads(bat_out)
    except Exception:
        status["battery"] = {"raw": bat_out}
    # Wifi info
    wifi_out, _, _ = safe_run("termux-wifi-connectioninfo", timeout=8)
    try:
        status["wifi"] = json.loads(wifi_out)
    except Exception:
        status["wifi"] = {"raw": wifi_out}
    # CPU load
    load_out, _, _ = safe_run("cat /proc/loadavg", timeout=5)
    status["load_avg"] = load_out
    # Memory
    mem_out, _, _ = safe_run("free -m | awk 'NR==2{print $2,$3,$4}'", timeout=5)
    mem_parts = mem_out.split()
    if len(mem_parts) == 3:
        status["memory_mb"] = {
            "total": mem_parts[0],
            "used": mem_parts[1],
            "free": mem_parts[2]
        }
    else:
        status["memory_mb"] = {"raw": mem_out}
    # Disk
    disk_out, _, _ = safe_run("df -h ~ | awk 'NR==2{print $2,$3,$4,$5}'", timeout=5)
    disk_parts = disk_out.split()
    if len(disk_parts) == 4:
        status["disk"] = {
            "total": disk_parts[0],
            "used": disk_parts[1],
            "avail": disk_parts[2],
            "use_pct": disk_parts[3]
        }
    else:
        status["disk"] = {"raw": disk_out}
    return status


# âââââââââââââââââââââââââââââââââââââââââââââ
# NTFY INTEGRATION
# âââââââââââââââââââââââââââââââââââââââââââââ
def ntfy_publish(message, title="TCC Bridge V2", priority="default", retries=3, delay=5):
    """Send a notification to ntfy with retry logic."""
    url = f"https://ntfy.sh/{NTFY_TOPIC}"
    for attempt in range(1, retries + 1):
        try:
            payload = message.encode("utf-8")
            req = Request(
                url,
                data=payload,
                method="POST",
                headers={
                    "Title": title,
                    "Priority": priority,
                    "Content-Type": "text/plain; charset=utf-8"
                }
            )
            with urlopen(req, timeout=10) as resp:
                if resp.status in (200, 201):
                    logger.debug(f"ntfy published OK (attempt {attempt})")
                    return True
        except (URLError, HTTPError) as e:
            logger.warning(f"ntfy attempt {attempt}/{retries} failed: {e}")
        except Exception as e:
            logger.error(f"ntfy unexpected error (attempt {attempt}): {e}")
        if attempt < retries:
            time.sleep(delay)
    logger.error("ntfy: all retry attempts exhausted")
    return False


# âââââââââââââââââââââââââââââââââââââââââââââ
# SUPABASE INTEGRATION
# âââââââââââââââââââââââââââââââââââââââââââââ
def supabase_upsert(table, record, retries=3, delay=5):
    """Upsert a record into a Supabase table with retry."""
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    for attempt in range(1, retries + 1):
        try:
            payload = json.dumps(record).encode("utf-8")
            req = Request(
                url,
                data=payload,
                method="POST",
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}",
                    "Content-Type": "application/json",
                    "Prefer": "resolution=merge-duplicates,return=minimal"
                }
            )
            with urlopen(req, timeout=10) as resp:
                logger.debug(f"Supabase upsert OK (attempt {attempt}) status={resp.status}")
                return True
        except HTTPError as e:
            body = ""
            try:
                body = e.read().decode("utf-8", errors="replace")
            except Exception:
                pass
            logger.warning(f"Supabase HTTP error attempt {attempt}/{retries}: {e.code} {body}")
        except URLError as e:
            logger.warning(f"Supabase URL error attempt {attempt}/{retries}: {e}")
        except Exception as e:
            logger.error(f"Supabase unexpected error (attempt {attempt}): {e}")
        if attempt < retries:
            time.sleep(delay)
    logger.error("Supabase: all retry attempts exhausted")
    return False


def supabase_heartbeat():
    """Send heartbeat record to Supabase."""
    record = {
        "device_id": "tcc-zenith",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "uptime_seconds": uptime_seconds(),
        "cloudflared_running": is_cloudflared_running(),
        "bridge_version": "2.0.0"
    }
    return supabase_upsert("device_heartbeats", record)


# âââââââââââââââââââââââââââââââââââââââââââââ
# HEARTBEAT LOOP
# âââââââââââââââââââââââââââââââââââââââââââââ
def heartbeat_loop():
    """Background thread: send heartbeat to ntfy + Supabase every HEARTBEAT_IV seconds."""
    logger.info("Heartbeat loop started")
    while not _shutdown_flag.is_set():
        try:
            up = uptime_seconds()
            cf = is_cloudflared_running()
            msg = (
                f"Bridge V2 alive | uptime={up}s | "
                f"cloudflared={'UP' if cf else 'DOWN'} | "
                f"port={SERVER_PORT}"
            )
            logger.info(f"[Heartbeat] {msg}")
            ntfy_publish(msg, title="TCC Heartbeat", priority="low")
            supabase_heartbeat()
        except Exception as e:
            logger.error(f"Heartbeat error: {e}\n{traceback.format_exc()}")
        _shutdown_flag.wait(timeout=HEARTBEAT_IV)
    logger.info("Heartbeat loop exiting")


# âââââââââââââââââââââââââââââââââââââââââââââ
# CLOUDFLARED WATCHDOG
# âââââââââââââââââââââââââââââââââââââââââââââ
def cloudflared_watchdog():
    """Background thread: restart cloudflared if it dies."""
    logger.info("Cloudflared watchdog started")
    restart_attempts = 0
    MAX_RESTART = 10
    while not _shutdown_flag.is_set():
        _shutdown_flag.wait(timeout=30)
        if _shutdown_flag.is_set():
            break
        try:
            if not is_cloudflared_running():
                if restart_attempts < MAX_RESTART:
                    restart_attempts += 1
                    logger.warning(f"cloudflared not running, restart attempt {restart_attempts}/{MAX_RESTART}")
                    stdout, stderr, rc = safe_run(
                        "nohup cloudflared tunnel run --url http://localhost:8765 >> ~/cloudflared.log 2>&1 &",
                        timeout=5
                    )
                    logger.info(f"cloudflared restart rc={rc} stdout={stdout} stderr={stderr}")
                    ntfy_publish(
                        f"cloudflared restarted (attempt {restart_attempts})",
                        title="TCC Watchdog",
                        priority="high"
                    )
                else:
                    logger.error("cloudflared max restart attempts reached, giving up auto-restart")
            else:
                restart_attempts = 0  # reset on healthy check
        except Exception as e:
            logger.error(f"Cloudflared watchdog error: {e}\n{traceback.format_exc()}")
    logger.info("Cloudflared watchdog exiting")


# âââââââââââââââââââââââââââââââââââââââââââââ
# COMMAND SAFETY FILTER
# âââââââââââââââââââââââââââââââââââââââââââââ
BLOCKED_PATTERNS = [
    "rm -rf /",
    "mkfs",
    "dd if=/dev/zero",
    ":(){ :|:& };",
    "> /dev/sda",
    "shutdown",
    "reboot",
    "halt",
    "poweroff"
]


def is_command_safe(cmd):
    """Block obviously dangerous commands."""
    lower = cmd.lower()
    for pattern in BLOCKED_PATTERNS:
        if pattern.lower() in lower:
            return False, f"Blocked pattern detected: {pattern}"
    return True, ""


# âââââââââââââââââââââââââââââââââââââââââââââ
# LOG READER
# âââââââââââââââââââââââââââââââââââââââââââââ
def read_last_log_lines(n=MAX_LOG_LINES):
    """Read last N lines from log file."""
    try:
        with open(LOG_FILE, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
        return lines[-n:]
    except FileNotFoundError:
        return []
    except Exception as e:
        logger.error(f"Log read error: {e}")
        return []


# âââââââââââââââââââââââââââââââââââââââââââââ
# HTTP HANDLER
# âââââââââââââââââââââââââââââââââââââââââââââ
class BridgeHandler(BaseHTTPRequestHandler):

    def log_message(self, format, *args):
        # Route access logs through our logger
        logger.debug(f"HTTP {self.address_string()} - {format % args}")

    def send_json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def send_error_json(self, msg, status=400):
        self.send_json({"ok": False, "error": msg}, status=status)

    def read_body(self):
        """Read and parse JSON body from request."""
        length = int(self.headers.get("Content-Length", 0))
        if length > 0:
            raw = self.rfile.read(length)
            try:
                return json.loads(raw.decode("utf-8"))
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON body: {e}")
        return {}

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/health":
            self.handle_health()
        elif path == "/log":
            self.handle_log()
        else:
            self.send_error_json(f"Unknown GET endpoint: {path}", status=404)

    def do_POST(self):
        path = urlparse(self.path).path
        try:
            body = self.read_body()
        except ValueError as e:
            self.send_error_json(str(e), status=400)
            return

        routes = {
            "/exec":       self.handle_exec,
            "/toast":      self.handle_toast,
            "/vibrate":    self.handle_vibrate,
            "/speak":      self.handle_speak,
            "/write_file": self.handle_write_file,
            "/restart":    self.handle_restart,
            "/log":        self.handle_log,
        }
        handler = routes.get(path)
        if handler:
            try:
                handler(body)
            except Exception as e:
                logger.error(f"Handler error [{path}]: {e}\n{traceback.format_exc()}")
                self.send_error_json(f"Internal error: {e}", status=500)
        else:
            self.send_error_json(f"Unknown POST endpoint: {path}", status=404)

    # ââ Endpoint Handlers ââ

    def handle_health(self, body=None):
        logger.info("GET /health")
        try:
            cf_running = is_cloudflared_running()
            net = get_network_status()
            dev = get_device_status()
            data = {
                "ok": True,
                "bridge_version": "2.0.0",
                "uptime_seconds": uptime_seconds(),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "cloudflared": {
                    "running": cf_running
                },
                "network": net,
                "device": dev
            }
            self.send_json(data)
        except Exception as e:
            logger.error(f"/health error: {e}\n{traceback.format_exc()}")
            self.send_error_json(str(e), status=500)

    def handle_exec(self, body):
        cmd = body.get("cmd", "").strip()
        if not cmd:
            self.send_error_json("Missing 'cmd' field")
            return
        safe, reason = is_command_safe(cmd)
        if not safe:
            logger.warning(f"/exec BLOCKED: {cmd} | reason: {reason}")
            self.send_error_json(f"Command blocked: {reason}", status=403)
            return
        timeout = min(int(body.get("timeout", 30)), 120)
        logger.info(f"/exec cmd={cmd!r} timeout={timeout}")
        stdout, stderr, rc = safe_run(cmd, timeout=timeout)
        self.send_json({
            "ok": rc == 0,
            "stdout": stdout,
            "stderr": stderr,
            "returncode": rc
        })

    def handle_toast(self, body):
        text = body.get("text", "").strip()
        if not text:
            self.send_error_json("Missing 'text' field")
            return
        duration = body.get("duration", "short")
        if duration not in ("short", "long"):
            duration = "short"
        logger.info(f"/toast text={text!r}")
        safe_text = text.replace('"', '\\"')
        cmd = f'termux-toast -d {duration} "{safe_text}"'
        stdout, stderr, rc = safe_run(cmd, timeout=10)
        self.send_json({"ok": rc == 0, "stdout": stdout, "stderr": stderr})

    def handle_vibrate(self, body):
        duration_ms = int(body.get("duration_ms", 300))
        duration_ms = max(50, min(duration_ms, 5000))
        logger.info(f"/vibrate duration_ms={duration_ms}")
        cmd = f"termux-vibrate -d {duration_ms}"
        stdout, stderr, rc = safe_run(cmd, timeout=10)
        self.send_json({"ok": rc == 0, "stdout": stdout, "stderr": stderr})

    def handle_speak(self, body):
        text = body.get("text", "").strip()
        if not text:
            self.send_error_json("Missing 'text' field")
            return
        rate = int(body.get("rate", 1))
        rate = max(0, min(rate, 3))
        language = body.get("language", "en")
        logger.info(f"/speak text={text!r} rate={rate}")
        safe_text = text.replace('"', '\\"')
        cmd = f'termux-tts-speak -r {rate} -l {language} "{safe_text}"'
        stdout, stderr, rc = safe_run(cmd, timeout=30)
        self.send_json({"ok": rc == 0, "stdout": stdout, "stderr": stderr})

    def handle_write_file(self, body):
        path = body.get("path", "").strip()
        content = body.get("content", "")
        if not path:
            self.send_error_json("Missing 'path' field")
            return
        # Resolve and restrict to home directory
        resolved = os.path.realpath(os.path.expanduser(path))
        home = os.path.realpath(os.path.expanduser("~"))
        if not resolved.startswith(home):
            logger.warning(f"/write_file path traversal attempt: {path}")
            self.send_error_json("Path must be within home directory", status=403)
            return
        mode = body.get("mode", "w")
        if mode not in ("w", "a"):
            mode = "w"
        logger.info(f"/write_file path={resolved!r} mode={mode}")
        try:
            os.makedirs(os.path.dirname(resolved), exist_ok=True)
            with open(resolved, mode, encoding="utf-8") as f:
                f.write(content)
            self.send_json({"ok": True, "path": resolved, "bytes_written": len(content)})
        except Exception as e:
            logger.error(f"/write_file error: {e}")
            self.send_error_json(str(e), status=500)

    def handle_log(self, body=None):
        logger.info("GET/POST /log")
        n = MAX_LOG_LINES
        if isinstance(body, dict):
            n = min(int(body.get("lines", MAX_LOG_LINES)), 500)
        lines = read_last_log_lines(n)
        self.send_json({
            "ok": True,
            "lines": len(lines),
            "log": "".join(lines)
        })

    def handle_restart(self, body):
        logger.warning("/restart called â restarting via PM2")
        ntfy_publish("Bridge V2 restart requested via /restart", title="TCC Bridge", priority="high")
        def do_restart():
            time.sleep(1)
            stdout, stderr, rc = safe_run("pm2 restart bridge_v2", timeout=15)
            logger.info(f"PM2 restart rc={rc} out={stdout} err={stderr}")
            if rc != 0:
                # Fallback: restart this script directly
                logger.warning("PM2 restart failed, attempting direct restart")
                safe_run(f"nohup python3 {os.path.abspath(__file__)} &", timeout=5)
        t = threading.Thread(target=do_restart, daemon=True)
        t.start()
        self.send_json({"ok": True, "message": "Restart initiated via PM2"})


# âââââââââââââââââââââââââââââââââââââââââââââ
# SERVER RUNNER
# âââââââââââââââââââââââââââââââââââââââââââââ
class ReusableTCPServer(HTTPServer):
    allow_reuse_address = True

    def handle_error(self, request, client_address):
        logger.error(
            f"Unhandled error from {client_address}:\n{traceback.format_exc()}"
        )


def start_server():
    server = ReusableTCPServer(("", SERVER_PORT), BridgeHandler)
    logger.info(f"Bridge V2 listening on port {SERVER_PORT}")
    return server


# âââââââââââââââââââââââââââââââââââââââââââââ
# SIGNAL HANDLERS
# âââââââââââââââââââââââââââââââââââââââââââââ
def _handle_signal(signum, frame):
    sig_name = signal.Signals(signum).name
    logger.info(f"Signal {sig_name} received, initiating graceful shutdown")
    _shutdown_flag.set()


signal.signal(signal.SIGTERM, _handle_signal)
signal.signal(signal.SIGINT, _handle_signal)


# âââââââââââââââââââââââââââââââââââââââââââââ
# MAIN
# âââââââââââââââââââââââââââââââââââââââââââââ
def main():
    logger.info("ââââââââââââââââââââââââââââââââââââ")
    logger.info(" TCC Bridge V2 starting up         ")
    logger.info(f" PID: {os.getpid()}                ")
    logger.info(f" Log: {LOG_FILE}                   ")
    logger.info(f" Port: {SERVER_PORT}               ")
    logger.info("ââââââââââââââââââââââââââââââââââââ")

    # Send startup notification
    ntfy_publish(
        f"Bridge V2 started | port={SERVER_PORT} | pid={os.getpid()}",
        title="TCC Bridge V2",
        priority="default"
    )
    supabase_heartbeat()

    # Start background threads
    hb_thread = threading.Thread(target=heartbeat_loop, daemon=True, name="heartbeat")
    hb_thread.start()

    wd_thread = threading.Thread(target=cloudflared_watchdog, daemon=True, name="cf-watchdog")
    wd_thread.start()

    # Start HTTP server
    server = start_server()
    server_thread = threading.Thread(target=server.serve_forever, daemon=True, name="http-server")
    server_thread.start()

    logger.info("All components running. Waiting for shutdown signal...")

    # Block main thread until shutdown
    _shutdown_flag.wait()

    logger.info("Shutdown flag set â stopping HTTP server")
    server.shutdown()
    server.server_close()
    ntfy_publish("Bridge V2 shutting down gracefully", title="TCC Bridge V2", priority="default")
    logger.info("Bridge V2 shutdown complete")
    sys.exit(0)


if __name__ == "__main__":
    main()
