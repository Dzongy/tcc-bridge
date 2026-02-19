#!/usr/bin/env python3
"""TCC Bridge v5.0 — BULLETPROOF EDITION
Permanent phone control HTTP server for Termux.
Endpoints: /exec, /toast, /speak, /vibrate, /write_file, /listen, /conversation, /health, /voice, /state-push, /tunnel-health
Features: Auto-reconnect, crash recovery, Supabase state push, health monitoring
Auth: X-Auth header token
"""
import subprocess
import json
import os
import sys
import base64
import signal
import logging
import time
import threading
import traceback
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.request import Request, urlopen
from urllib.parse import urlparse

# ── Config ──
AUTH_TOKEN   = os.environ.get("BRIDGE_AUTH",    "amos-bridge-2026")
PORT         = int(os.environ.get("BRIDGE_PORT", "8080"))
LOG_FILE     = os.path.expanduser("~/bridge.log")
SUPABASE_URL = os.environ.get("SUPABASE_URL",   "https://vbqbbziqleymxcyesmky.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY",   "")
NTFY_TOPIC   = os.environ.get("NTFY_TOPIC",     "tcc-zenith-hive")
HEALTH_INTERVAL = 300          # 5 minutes between Supabase pushes
VERSION      = "5.0.0"
START_TIME   = time.time()
DEVICE_ID    = "amos-arms"

# ── Logging (file + stderr) ──
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stderr),
    ],
)
log = logging.getLogger("bridge")


# ════════════════════════════════════════════════
# UTILITIES
# ════════════════════════════════════════════════

def kill_port(port: int):
    """Kill every process holding *port* except our own PID."""
    my_pid = os.getpid()
    try:
        r = subprocess.run(
            f"lsof -ti:{port}", shell=True, capture_output=True, text=True
        )
        for pid in r.stdout.strip().split():
            if pid and int(pid) != my_pid:
                try:
                    os.kill(int(pid), signal.SIGTERM)
                    log.info("Killed stale PID %s on port %d", pid, port)
                except ProcessLookupError:
                    pass
    except Exception:
        pass


def _run(cmd: str, timeout: int = 10) -> subprocess.CompletedProcess:
    """Convenience wrapper around subprocess.run."""
    return subprocess.run(
        cmd, shell=True, capture_output=True, text=True, timeout=timeout
    )


def get_battery() -> dict:
    """Return parsed termux-battery-status or empty dict."""
    try:
        r = _run("termux-battery-status", timeout=10)
        if r.returncode == 0 and r.stdout.strip():
            return json.loads(r.stdout)
    except Exception:
        pass
    return {}


def get_network() -> str:
    """Return best-effort network description."""
    # Try telephony info first (cellular)
    try:
        r = _run("termux-telephony-deviceinfo", timeout=10)
        if r.returncode == 0 and r.stdout.strip():
            info = json.loads(r.stdout)
            network_type = info.get("data_network_type", "")
            if network_type and network_type != "UNKNOWN":
                return network_type
    except Exception:
        pass
    # Fallback: routing table
    try:
        r = _run("ip route get 1.1.1.1 2>/dev/null | head -1", timeout=5)
        if r.stdout.strip():
            return r.stdout.strip()
    except Exception:
        pass
    return "unknown"


def get_device_info() -> dict:
    """Assemble the canonical device-state dict used by /health and Supabase."""
    battery  = get_battery()
    network  = get_network()
    uptime   = int(time.time() - START_TIME)

    info = {
        "status":          "ok",
        "version":         VERSION,
        "uptime":          uptime,          # seconds
        "battery":         battery,
        "network":         network,
        "device_id":       DEVICE_ID,
        "port":            PORT,
    }
    # hostname (nice to have)
    try:
        info["hostname"] = _run("hostname", timeout=5).stdout.strip()
    except Exception:
        info["hostname"] = "unknown"
    return info


# ════════════════════════════════════════════════
# SUPABASE
# ════════════════════════════════════════════════

def push_state_to_supabase(data: dict | None = None):
    """Push device state to 'device_state' table in Supabase.

    Schema expected:
        id          uuid PRIMARY KEY DEFAULT gen_random_uuid()
        device_id   text UNIQUE
        last_seen   timestamptz DEFAULT now()
        status      text
        uptime      int
        battery_pct int
        battery_raw jsonb
        network     text
        version     text
        hostname    text
        raw_output  jsonb
    """
    if not SUPABASE_KEY:
        log.debug("SUPABASE_KEY not set — skipping push")
        return
    if data is None:
        data = get_device_info()

    battery = data.get("battery", {})
    battery_pct = battery.get("percentage", -1) if isinstance(battery, dict) else -1

    payload = json.dumps({
        "device_id":   DEVICE_ID,
        "last_seen":   time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "status":      data.get("status", "ok"),
        "uptime":      data.get("uptime", 0),
        "battery_pct": battery_pct,
        "battery_raw": battery if isinstance(battery, dict) else {},
        "network":     data.get("network", "unknown"),
        "version":     data.get("version", VERSION),
        "hostname":    data.get("hostname", "unknown"),
        "raw_output":  data,
    }).encode("utf-8")

    try:
        req = Request(
            f"{SUPABASE_URL}/rest/v1/device_state",
            data=payload,
            method="POST",
        )
        req.add_header("apikey",        SUPABASE_KEY)
        req.add_header("Authorization", f"Bearer {SUPABASE_KEY}")
        req.add_header("Content-Type",  "application/json")
        req.add_header("Prefer",        "resolution=merge-duplicates,return=minimal")
        urlopen(req, timeout=15)
        log.info("Supabase state push OK (battery=%s%%)", battery_pct)
    except Exception as e:
        log.warning("Supabase push failed: %s", e)


# ════════════════════════════════════════════════
# NTFY
# ════════════════════════════════════════════════

def send_ntfy(title: str, message: str, priority: int = 3, tags: list = None):
    try:
        payload = json.dumps({
            "topic":    NTFY_TOPIC,
            "title":   title,
            "message": message,
            "priority": priority,
            "tags":    tags or ["robot"],
        }).encode("utf-8")
        req = Request("https://ntfy.sh", data=payload, method="POST")
        req.add_header("Content-Type", "application/json")
        urlopen(req, timeout=10)
    except Exception as e:
        log.warning("ntfy send failed: %s", e)


# ════════════════════════════════════════════════
# HEALTH MONITOR THREAD
# ════════════════════════════════════════════════

def _try_restart_cloudflared():
    cf_cfg = os.path.expanduser("~/.cloudflared/config.yml")
    subprocess.Popen(
        f"nohup cloudflared tunnel --config {cf_cfg} run "
        f"> $HOME/cloudflared.log 2>&1 &",
        shell=True,
    )
    time.sleep(6)
    r = _run("pgrep -f cloudflared")
    return r.returncode == 0


def _rotate_log():
    try:
        if os.path.getsize(LOG_FILE) > 5 * 1024 * 1024:   # 5 MB
            with open(LOG_FILE, "r") as fh:
                lines = fh.readlines()
            with open(LOG_FILE, "w") as fh:
                fh.writelines(lines[-1000:])
            log.info("Log rotated — kept last 1000 lines")
    except Exception:
        pass


def health_monitor():
    """Background daemon: push state every 5 min, watch cloudflared."""
    while True:
        try:
            time.sleep(HEALTH_INTERVAL)

            info = get_device_info()
            push_state_to_supabase(info)

            # ── Cloudflared watchdog ──
            r = _run("pgrep -f cloudflared")
            if r.returncode != 0:
                log.warning("cloudflared NOT running — attempting auto-restart")
                send_ntfy(
                    "BRIDGE ALERT: Tunnel Down",
                    "cloudflared not found. Auto-restarting…",
                    priority=5, tags=["warning", "rotating_light"],
                )
                if _try_restart_cloudflared():
                    log.info("cloudflared restarted OK")
                    send_ntfy("Bridge Recovery", "cloudflared restarted successfully",
                              priority=3, tags=["check"])
                else:
                    log.error("cloudflared restart FAILED")
                    send_ntfy("BRIDGE CRITICAL",
                              "cloudflared restart FAILED. Manual intervention needed.",
                              priority=5, tags=["skull"])

            _rotate_log()

        except Exception as e:
            log.error("Health monitor error: %s", e)


# ════════════════════════════════════════════════
# HTTP HANDLER
# ════════════════════════════════════════════════

class BridgeHandler(BaseHTTPRequestHandler):

    # ── Auth / helpers ──────────────────────────
    def _auth(self) -> bool:
        if self.headers.get("X-Auth", "") != AUTH_TOKEN:
            self._respond(401, {"error": "unauthorized"})
            return False
        return True

    def _respond(self, code: int, data: dict):
        body = json.dumps(data).encode()
        self.send_response(code)
        self.send_header("Content-Type",   "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin",  "*")
        self.send_header("Access-Control-Allow-Headers", "X-Auth, Content-Type")
        self.end_headers()
        self.wfile.write(body)

    def _body(self) -> dict:
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return {}
        raw = self.rfile.read(length)
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {}

    def log_message(self, fmt, *args):   # redirect to our logger
        log.info(fmt, *args)

    # ── CORS pre-flight ─────────────────────────
    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin",  "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "X-Auth, Content-Type")
        self.end_headers()

    # ── GET ─────────────────────────────────────
    def do_GET(self):
        path = urlparse(self.path).path

        if path == "/health":
            # Public endpoint — no auth required
            info = get_device_info()      # {status, uptime, battery, network, version, …}
            self._respond(200, info)
            return

        if path == "/tunnel-health":
            if not self._auth():
                return
            info = get_device_info()
            r = _run("pgrep -f cloudflared")
            info["cloudflared_running"] = r.returncode == 0
            info["status"] = "ok" if r.returncode == 0 else "tunnel_down"
            self._respond(200, info)
            return

        self._respond(404, {"error": "not found"})

    # ── POST ────────────────────────────────────
    def do_POST(self):
        path = urlparse(self.path).path
        if not self._auth():
            return

        try:
            # ── /exec ──────────────────────────
            if path == "/exec":
                body    = self._body()
                cmd     = body.get("command", "echo hello")
                timeout = int(body.get("timeout", 30))
                r = subprocess.run(
                    cmd, shell=True, capture_output=True, text=True, timeout=timeout
                )
                self._respond(200, {
                    "stdout": r.stdout,
                    "stderr": r.stderr,
                    "code":   r.returncode,
                })

            # ── /toast ─────────────────────────
            elif path == "/toast":
                body = self._body()
                msg  = body.get("message", "Hello from Bridge")
                subprocess.run(f'termux-toast "{msg}"', shell=True, timeout=5)
                self._respond(200, {"ok": True})

            # ── /speak ─────────────────────────
            elif path == "/speak":
                body = self._body()
                text = body.get("text", "Bridge speaking")
                subprocess.run(f'termux-tts-speak "{text}"', shell=True, timeout=30)
                self._respond(200, {"ok": True})

            # ── /vibrate ───────────────────────
            elif path == "/vibrate":
                body = self._body()
                ms   = int(body.get("duration", 500))
                subprocess.run(f"termux-vibrate -d {ms}", shell=True, timeout=5)
                self._respond(200, {"ok": True})

            # ── /write_file ────────────────────
            elif path == "/write_file":
                body    = self._body()
                fpath   = os.path.expanduser(body.get("path", "~/bridge_output.txt"))
                content = body.get("content", "")
                if body.get("base64"):
                    content = base64.b64decode(content).decode("utf-8", errors="replace")
                parent = os.path.dirname(fpath)
                if parent:
                    os.makedirs(parent, exist_ok=True)
                with open(fpath, "w") as fh:
                    fh.write(content)
                self._respond(200, {"ok": True, "path": fpath})

            # ── /listen ────────────────────────
            elif path == "/listen":
                wav = os.path.expanduser("~/listen.wav")
                subprocess.run(
                    "termux-microphone-record -f ~/listen.wav -l 5",
                    shell=True, timeout=10
                )
                time.sleep(5)
                subprocess.run("termux-microphone-record -q", shell=True, timeout=5)
                if os.path.exists(wav):
                    with open(wav, "rb") as fh:
                        audio_b64 = base64.b64encode(fh.read()).decode()
                    self._respond(200, {"audio_base64": audio_b64})
                else:
                    self._respond(500, {"error": "recording failed"})

            # ── /conversation ──────────────────
            elif path == "/conversation":
                body = self._body()
                text = body.get("text", "Hello from the bridge")
                wav  = os.path.expanduser("~/conv.wav")
                subprocess.run(f'termux-tts-speak "{text}"', shell=True, timeout=30)
                time.sleep(1)
                subprocess.run(
                    "termux-microphone-record -f ~/conv.wav -l 5",
                    shell=True, timeout=10
                )
                time.sleep(5)
                subprocess.run("termux-microphone-record -q", shell=True, timeout=5)
                audio_b64 = None
                if os.path.exists(wav):
                    with open(wav, "rb") as fh:
                        audio_b64 = base64.b64encode(fh.read()).decode()
                self._respond(200, {"spoken": text, "audio_base64": audio_b64})

            # ── /voice ─────────────────────────
            elif path == "/voice":
                body   = self._body()
                text   = body.get("text", "")
                engine = body.get("engine", "termux")
                if engine == "termux" and text:
                    subprocess.run(f'termux-tts-speak "{text}"', shell=True, timeout=30)
                self._respond(200, {"ok": True})

            # ── /state-push ────────────────────
            elif path == "/state-push":
                info = get_device_info()
                push_state_to_supabase(info)
                self._respond(200, {"ok": True, "pushed": info})

            else:
                self._respond(404, {"error": "not found"})

        except subprocess.TimeoutExpired:
            self._respond(504, {"error": "command timeout"})
        except Exception as e:
            log.error("Handler error on %s: %s\n%s", path, e, traceback.format_exc())
            self._respond(500, {"error": str(e)})


# ════════════════════════════════════════════════
# SERVER RUNNER
# ════════════════════════════════════════════════

def run_server():
    max_retries = 15
    for attempt in range(1, max_retries + 1):
        try:
            kill_port(PORT)
            time.sleep(1)
            server = HTTPServer(("0.0.0.0", PORT), BridgeHandler)
            log.info("TCC Bridge v%s ONLINE — port %d (attempt %d)", VERSION, PORT, attempt)
            send_ntfy(
                f"Bridge v{VERSION} ONLINE",
                f"TCC Bridge running on port {PORT}. Health monitor active.",
                priority=3, tags=["rocket", "check"],
            )
            server.serve_forever()
            break   # clean shutdown
        except OSError as e:
            if "Address already in use" in str(e):
                log.warning("Port %d busy — retry %d/%d", PORT, attempt, max_retries)
                kill_port(PORT)
                time.sleep(2)
            else:
                raise
        except KeyboardInterrupt:
            log.info("Bridge: KeyboardInterrupt — shutting down")
            return
        except Exception as e:
            log.error("Server crashed (attempt %d): %s\n%s", attempt, e, traceback.format_exc())
            log.info("Restarting in 3 s…")
            time.sleep(3)

    else:
        log.error("Failed to start after %d attempts — exiting", max_retries)
        sys.exit(1)


# ════════════════════════════════════════════════
# ENTRY POINT
# ════════════════════════════════════════════════

if __name__ == "__main__":
    log.info("=" * 60)
    log.info("TCC Bridge v%s — BULLETPROOF EDITION", VERSION)
    log.info("=" * 60)

    monitor = threading.Thread(target=health_monitor, daemon=True)
    monitor.start()
    log.info("Health monitor started (interval: %d s)", HEALTH_INTERVAL)

    # Outer crash-restart loop
    while True:
        try:
            run_server()
        except SystemExit:
            log.info("SystemExit received — bridge terminated")
            break
        except Exception as e:
            log.error("Fatal outer error: %s. Restarting in 5 s…", e)
            send_ntfy(
                "BRIDGE CRASH",
                f"Fatal error: {e}. Auto-restarting in 5 s…",
                priority=5, tags=["skull"],
            )
            time.sleep(5)
