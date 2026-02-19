#!/usr/bin/env python3
"""TCC Bridge v5.0 — BULLETPROOF EDITION
Permanent phone control HTTP server for Termux.
Endpoints: /exec, /toast, /speak, /vibrate, /write_file, /listen, /conversation, /health, /voice
Features: Auto-reconnect, crash recovery, Supabase state push, health monitoring
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
import time
import threading
import traceback
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.request import Request, urlopen
from urllib.error import URLError
from urllib.parse import parse_qs, urlparse

# ── Config ──
AUTH_TOKEN = os.environ.get("BRIDGE_AUTH", "amos-bridge-2026")
PORT = int(os.environ.get("BRIDGE_PORT", "8080"))
LOG_FILE = os.path.expanduser("~/bridge.log")
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://vbqbbziqleymxcyesmky.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")
NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "tcc-zenith-hive")
HEALTH_INTERVAL = 300  # 5 minutes between health pushes
VERSION = "5.1.0"
START_TIME = time.time()

# ── Logging setup (file + stderr, with rotation) ──
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
    """Kill any process holding the port. Skips own PID."""
    my_pid = os.getpid()
    try:
        r = subprocess.run(
            f"lsof -ti:{port}", shell=True, capture_output=True, text=True
        )
        pids = r.stdout.strip().split()
        for pid in pids:
            if pid and int(pid) != my_pid:
                os.kill(int(pid), signal.SIGTERM)
                log.info("Killed stale process %s on port %d", pid, port)
    except Exception:
        pass


def get_device_info():
    """Gather device state for health reporting."""
    info = {"version": VERSION, "uptime_seconds": int(time.time() - START_TIME), "port": PORT}
    try:
        r = subprocess.run("termux-battery-status", shell=True, capture_output=True, text=True, timeout=10)
        if r.returncode == 0:
            info["battery"] = json.loads(r.stdout)
    except Exception:
        pass
    try:
        r = subprocess.run("hostname", shell=True, capture_output=True, text=True, timeout=5)
        info["hostname"] = r.stdout.strip()
    except Exception:
        pass
    try:
        r = subprocess.run("ip route get 1.1.1.1 2>/dev/null | head -1", shell=True, capture_output=True, text=True, timeout=5)
        info["network"] = r.stdout.strip()
    except Exception:
        pass
    return info


def push_to_supabase(data):
    """Push device state to Supabase for backup monitoring."""
    if not SUPABASE_KEY:
        return
    try:
        payload = json.dumps({
            "device_id": "amos-arms",
            "battery": data.get("battery", {}).get("percentage", -1),
            "hostname": data.get("hostname", "unknown"),
            "network": data.get("network", "unknown"),
            "android_version": data.get("android_version", "unknown"),
            "raw_output": json.dumps(data),
        }).encode("utf-8")
        req = Request(
            f"{SUPABASE_URL}/rest/v1/device_state",
            data=payload,
            method="POST",
        )
        req.add_header("apikey", SUPABASE_KEY)
        req.add_header("Authorization", f"Bearer {SUPABASE_KEY}")
        req.add_header("Content-Type", "application/json")
        req.add_header("Prefer", "resolution=merge-duplicates")
        urlopen(req, timeout=10)
        log.info("Supabase state push OK")
    except Exception as e:
        log.warning("Supabase push failed: %s", e)


def send_ntfy(title, message, priority=3, tags=None):
    """Send notification via ntfy."""
    try:
        payload = json.dumps({
            "topic": NTFY_TOPIC,
            "title": title,
            "message": message,
            "priority": priority,
            "tags": tags or ["robot"],
        }).encode("utf-8")
        req = Request("https://ntfy.sh", data=payload, method="POST")
        req.add_header("Content-Type", "application/json")
        urlopen(req, timeout=10)
    except Exception as e:
        log.warning("ntfy send failed: %s", e)


def health_monitor():
    """Background thread: push health state and check tunnel periodically."""
    while True:
        try:
            time.sleep(HEALTH_INTERVAL)
            info = get_device_info()
            push_to_supabase(info)
            
            # Check if cloudflared is running
            r = subprocess.run("pgrep -f cloudflared", shell=True, capture_output=True, text=True)
            if r.returncode != 0:
                log.warning("cloudflared NOT running! Attempting restart...")
                send_ntfy(
                    "BRIDGE ALERT: Tunnel Down",
                    "cloudflared process not found. Attempting auto-restart.",
                    priority=5,
                    tags=["warning", "rotating_light"],
                )
                # Try to restart cloudflared
                subprocess.Popen(
                    "nohup cloudflared tunnel --config $HOME/.cloudflared/config.yml run > $HOME/cloudflared.log 2>&1 &",
                    shell=True,
                )
                time.sleep(5)
                # Verify restart
                r2 = subprocess.run("pgrep -f cloudflared", shell=True, capture_output=True, text=True)
                if r2.returncode == 0:
                    log.info("cloudflared restarted successfully")
                    send_ntfy("Bridge Recovery", "cloudflared auto-restarted successfully", priority=3, tags=["check"])
                else:
                    send_ntfy("BRIDGE CRITICAL", "cloudflared restart FAILED. Manual intervention needed.", priority=5, tags=["skull"])
            
            # Log rotation: trim log if > 5MB
            try:
                if os.path.getsize(LOG_FILE) > 5 * 1024 * 1024:
                    with open(LOG_FILE, "r") as f:
                        lines = f.readlines()
                    with open(LOG_FILE, "w") as f:
                        f.writelines(lines[-1000:])
                    log.info("Log rotated (kept last 1000 lines)")
            except Exception:
                pass
                
        except Exception as e:
            log.error("Health monitor error: %s", e)


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
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "X-Auth, Content-Type")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def _body(self):
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return {}
        return json.loads(self.rfile.read(length))

    def log_message(self, fmt, *args):
        log.info(fmt, *args)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "X-Auth, Content-Type")
        self.end_headers()

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/health":
            info = get_device_info()
            info["status"] = "ok"
            info["tunnel_check"] = "use /tunnel-health for full check"
            self._respond(200, info)
        elif path == "/tunnel-health":
            if not self._auth():
                return
            info = get_device_info()
            # Check cloudflared
            r = subprocess.run("pgrep -f cloudflared", shell=True, capture_output=True, text=True)
            info["cloudflared_running"] = r.returncode == 0
            info["status"] = "ok" if r.returncode == 0 else "tunnel_down"
            self._respond(200, info)
        else:
            self._respond(404, {"error": "not found"})

    def do_POST(self):
        path = urlparse(self.path).path
        if not self._auth():
            return

        try:
            if path == "/exec":
                body = self._body()
                cmd = body.get("command", "echo hello")
                timeout = body.get("timeout", 30)
                r = subprocess.run(
                    cmd, shell=True, capture_output=True, text=True, timeout=timeout
                )
                self._respond(200, {
                    "stdout": r.stdout,
                    "stderr": r.stderr,
                    "code": r.returncode,
                })

            elif path == "/toast":
                body = self._body()
                msg = body.get("message", "Hello from Bridge")
                subprocess.run(f'termux-toast "{msg}"', shell=True, timeout=5)
                self._respond(200, {"ok": True})

            elif path == "/speak":
                body = self._body()
                text = body.get("text", "Bridge speaking")
                subprocess.run(f'termux-tts-speak "{text}"', shell=True, timeout=30)
                self._respond(200, {"ok": True})

            elif path == "/vibrate":
                body = self._body()
                ms = body.get("duration", 500)
                subprocess.run(f"termux-vibrate -d {ms}", shell=True, timeout=5)
                self._respond(200, {"ok": True})

            elif path == "/write_file":
                body = self._body()
                fpath = os.path.expanduser(body.get("path", "~/bridge_output.txt"))
                content = body.get("content", "")
                if body.get("base64"):
                    content = base64.b64decode(content).decode("utf-8", errors="replace")
                os.makedirs(os.path.dirname(fpath), exist_ok=True)
                with open(fpath, "w") as f:
                    f.write(content)
                self._respond(200, {"ok": True, "path": fpath})

            elif path == "/listen":
                subprocess.run("termux-microphone-record -f ~/listen.wav -l 5", shell=True, timeout=10)
                time.sleep(5)
                subprocess.run("termux-microphone-record -q", shell=True, timeout=5)
                if os.path.exists(os.path.expanduser("~/listen.wav")):
                    with open(os.path.expanduser("~/listen.wav"), "rb") as f:
                        audio_b64 = base64.b64encode(f.read()).decode()
                    self._respond(200, {"audio_base64": audio_b64})
                else:
                    self._respond(500, {"error": "recording failed"})

            elif path == "/conversation":
                body = self._body()
                text = body.get("text", "Hello from the bridge")
                subprocess.run(f'termux-tts-speak "{text}"', shell=True, timeout=30)
                time.sleep(1)
                subprocess.run("termux-microphone-record -f ~/conv.wav -l 5", shell=True, timeout=10)
                time.sleep(5)
                subprocess.run("termux-microphone-record -q", shell=True, timeout=5)
                if os.path.exists(os.path.expanduser("~/conv.wav")):
                    with open(os.path.expanduser("~/conv.wav"), "rb") as f:
                        audio_b64 = base64.b64encode(f.read()).decode()
                    self._respond(200, {"spoken": text, "audio_base64": audio_b64})
                else:
                    self._respond(200, {"spoken": text, "audio_base64": None})

            elif path == "/voice":
                body = self._body()
                text = body.get("text", "")
                engine = body.get("engine", "termux")
                if engine == "termux":
                    subprocess.run(f'termux-tts-speak "{text}"', shell=True, timeout=30)
                self._respond(200, {"ok": True})

            elif path == "/state-push":
                """Manual trigger for Supabase state push."""
                info = get_device_info()
                push_to_supabase(info)
                self._respond(200, {"ok": True, "pushed": info})

            else:
                self._respond(404, {"error": "not found"})

        except subprocess.TimeoutExpired:
            self._respond(504, {"error": "command timeout"})
        except Exception as e:
            log.error("Handler error: %s\n%s", e, traceback.format_exc())
            self._respond(500, {"error": str(e)})


def run_server():
    """Start the HTTP server with retry logic."""
    max_retries = 10
    for attempt in range(max_retries):
        try:
            kill_port(PORT)
            time.sleep(1)
            server = HTTPServer(("0.0.0.0", PORT), BridgeHandler)
            log.info("TCC Bridge v%s ONLINE on port %d (attempt %d)", VERSION, PORT, attempt + 1)
            
            # Announce startup
            send_ntfy(
                f"Bridge v{VERSION} ONLINE",
                f"TCC Bridge started on port {PORT}. Health monitor active.",
                priority=3,
                tags=["rocket", "check"],
            )
            
            server.serve_forever()
        except OSError as e:
            if "Address already in use" in str(e):
                log.warning("Port %d busy, retry %d/%d...", PORT, attempt + 1, max_retries)
                kill_port(PORT)
                time.sleep(2)
            else:
                raise
        except KeyboardInterrupt:
            log.info("Bridge shutdown requested")
            break
        except Exception as e:
            log.error("Server crashed: %s\n%s", e, traceback.format_exc())
            log.info("Restarting in 3 seconds...")
            time.sleep(3)

    log.error("Failed to start after %d attempts", max_retries)
    sys.exit(1)


if __name__ == "__main__":
    log.info("=" * 60)
    log.info("TCC Bridge v%s — BULLETPROOF EDITION", VERSION)
    log.info("=" * 60)
    
    # Start health monitor in background
    monitor = threading.Thread(target=health_monitor, daemon=True)
    monitor.start()
    log.info("Health monitor started (interval: %ds)", HEALTH_INTERVAL)
    
    # Run the server (with auto-restart on crash)
    while True:
        try:
            run_server()
        except SystemExit:
            break
        except Exception as e:
            log.error("Fatal: %s. Restarting in 5s...", e)
            send_ntfy("BRIDGE CRASH", f"Fatal error: {e}. Auto-restarting...", priority=5, tags=["skull"])
            time.sleep(5)
