#!/usr/bin/env python3
"""
TCC BRIDGE V2 — CONSOLIDATED & BULLETPROOF
Kael the God Builder Edition
- All endpoints: /health, /exec, /toast, /speak, /vibrate, /write_file, /listen, /conversation, /voice
- Auto-reconnect & robust server binding
- ntfy critical error logging
- Supabase state persistence
- PM2 Optimized
"""

import os, json, time, threading, subprocess, logging, socket, sys, traceback, signal
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
from urllib.parse import urlparse, parse_qs

# ─── CONFIG ───────────────────────────────────────────────────────────────────
CONFIG = {
    "PORT":          int(os.environ.get("PORT", 8765)),
    "NTFY_TOPIC":    os.environ.get("NTFY_TOPIC",  "zenith-escape"),
    "NTFY_HIVE":     os.environ.get("NTFY_HIVE",   "tcc-zenith-hive"),
    "SUPABASE_URL":  os.environ.get("SUPABASE_URL", "https://vbqbbziqleymxcyesmky.supabase.co"),
    "SUPABASE_KEY":  os.environ.get("SUPABASE_KEY", "sb_secret_lIbl-DBgdnrt_fejgJjKqg_qR62SVEm"),
    "DEVICE_ID":     os.environ.get("DEVICE_ID",    socket.gethostname()),
    "VERSION":       "2.0.0-godbuilder",
    "FILES_DIR":     os.path.expanduser("~/tcc-bridge-files"),
    "LOG_FILE":      os.path.expanduser("~/tcc-bridge.log"),
    "RESTART_DELAY": 3,
    "MAX_RESTARTS":  10,
}

# ─── LOGGING ──────────────────────────────────────────────────────────────────
os.makedirs(CONFIG["FILES_DIR"], exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(CONFIG["LOG_FILE"], encoding="utf-8"),
    ]
)
log = logging.getLogger("TCC_BRIDGE_V2")

START_TIME = time.time()

# ─── NTFY HELPER ──────────────────────────────────────────────────────────────
def ntfy_alert(title: str, message: str, topic: str = None, tags: str = "warning,robot", priority: str = "high"):
    """Send a notification via ntfy.sh. Fire-and-forget."""
    topic = topic or CONFIG["NTFY_HIVE"]
    try:
        req = Request(
            f"https://ntfy.sh/{topic}",
            data=message.encode("utf-8"),
            method="POST",
        )
        req.add_header("Title",    title)
        req.add_header("Tags",     tags)
        req.add_header("Priority", priority)
        urlopen(req, timeout=8)
    except Exception as exc:
        log.warning(f"[ntfy] Failed to send alert: {exc}")

# ─── SUPABASE HELPER ──────────────────────────────────────────────────────────
def supabase_upsert(table: str, payload: dict) -> bool:
    """Upsert a row into a Supabase table via REST. Returns True on success."""
    try:
        url  = f"{CONFIG['SUPABASE_URL']}/rest/v1/{table}"
        body = json.dumps(payload).encode("utf-8")
        req  = Request(url, data=body, method="POST")
        req.add_header("apikey",        CONFIG["SUPABASE_KEY"])
        req.add_header("Authorization", f"Bearer {CONFIG['SUPABASE_KEY']}")
        req.add_header("Content-Type",  "application/json")
        req.add_header("Prefer",        "resolution=merge-duplicates,return=minimal")
        urlopen(req, timeout=10)
        return True
    except Exception as exc:
        log.warning(f"[supabase] Upsert failed: {exc}")
        return False

def push_state(extra: dict = None):
    """Push basic device state to Supabase device_state table."""
    payload = {
        "device_id":  CONFIG["DEVICE_ID"],
        "last_seen":  time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "version":    CONFIG["VERSION"],
        "uptime_sec": int(time.time() - START_TIME),
    }
    if extra:
        payload.update(extra)
    supabase_upsert("device_state", payload)

# ─── TERMUX HELPERS ───────────────────────────────────────────────────────────
def termux_run(*args, timeout=30) -> dict:
    """Run a termux-api command and return result dict."""
    try:
        res = subprocess.run(
            list(args), capture_output=True, text=True, timeout=timeout
        )
        return {"stdout": res.stdout, "stderr": res.stderr, "code": res.returncode}
    except subprocess.TimeoutExpired:
        return {"stdout": "", "stderr": "timeout", "code": -1}
    except FileNotFoundError:
        return {"stdout": "", "stderr": f"command not found: {args[0]}", "code": 127}

# ─── HTTP HANDLER ─────────────────────────────────────────────────────────────
class BridgeHandler(BaseHTTPRequestHandler):

    # Silence default request logging (PM2 handles it)
    def log_message(self, fmt, *args):
        log.debug(f"[HTTP] {self.address_string()} — {fmt % args}")

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return {}
        raw = self.rfile.read(length)
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {}

    def _send_json(self, data: dict, status: int = 200):
        body = json.dumps(data, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type",   "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _send_cors(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin",  "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Auth")
        self.end_headers()

    # ── OPTIONS (CORS pre-flight) ──────────────────────────────────────────────
    def do_OPTIONS(self):
        self._send_cors()

    # ── GET endpoints ─────────────────────────────────────────────────────────
    def do_GET(self):
        parsed = urlparse(self.path)
        path   = parsed.path
        query  = parse_qs(parsed.query)

        try:
            if path == "/health":
                self._send_json({
                    "status":  "online",
                    "uptime":  round(time.time() - START_TIME, 2),
                    "device":  CONFIG["DEVICE_ID"],
                    "version": CONFIG["VERSION"],
                    "time":    time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                })

            elif path == "/speak":
                text = query.get("text", [""])[0].strip()
                if not text:
                    self._send_json({"error": "missing ?text= parameter"}, 400)
                    return
                r = termux_run("termux-tts-speak", text)
                self._send_json({"status": "spoken", "text": text, **r})

            elif path == "/listen":
                duration = query.get("duration", ["5"])[0]
                outfile  = os.path.join(CONFIG["FILES_DIR"], "listen_latest.mp3")
                r = termux_run("termux-microphone-record", "-d", duration, "-f", outfile, timeout=int(duration)+10)
                self._send_json({"status": "recorded", "file": outfile, **r})

            elif path == "/voice":
                # Return last recorded audio file path
                outfile = os.path.join(CONFIG["FILES_DIR"], "listen_latest.mp3")
                exists  = os.path.isfile(outfile)
                self._send_json({"file": outfile, "exists": exists})

            else:
                self._send_json({"error": "not found", "path": path}, 404)

        except Exception as e:
            self._handle_exception(e)

    # ── POST endpoints ────────────────────────────────────────────────────────
    def do_POST(self):
        data = self._read_json()
        path = urlparse(self.path).path

        try:
            if path == "/exec":
                cmd = data.get("command", "")
                if not cmd:
                    self._send_json({"error": "missing 'command' field"}, 400)
                    return
                timeout = int(data.get("timeout", 30))
                res = subprocess.run(
                    cmd, shell=True, capture_output=True, text=True, timeout=timeout
                )
                self._send_json({"stdout": res.stdout, "stderr": res.stderr, "code": res.returncode})

            elif path == "/toast":
                text = data.get("text", "Hello from TCC Bridge!")
                short = data.get("short", False)
                args  = ["termux-toast"]
                if short:
                    args += ["-s"]
                args.append(text)
                r = termux_run(*args)
                self._send_json({"status": "toasted", "text": text, **r})

            elif path == "/speak":
                text = data.get("text", "")
                if not text:
                    self._send_json({"error": "missing 'text' field"}, 400)
                    return
                lang   = data.get("lang",   "en")
                engine = data.get("engine", "")
                args   = ["termux-tts-speak", "-l", lang]
                if engine:
                    args += ["-e", engine]
                args.append(text)
                r = termux_run(*args, timeout=60)
                self._send_json({"status": "spoken", "text": text, **r})

            elif path == "/vibrate":
                duration = int(data.get("duration", 500))
                force    = data.get("force", False)
                args     = ["termux-vibrate", "-d", str(duration)]
                if force:
                    args.append("-f")
                r = termux_run(*args)
                self._send_json({"status": "vibrated", "duration": duration, **r})

            elif path == "/write_file":
                filename = data.get("filename", "")
                content  = data.get("content",  "")
                if not filename:
                    self._send_json({"error": "missing 'filename' field"}, 400)
                    return
                # Sanitise: strip leading slashes/traversal
                safe_name = os.path.basename(filename)
                dest_dir  = data.get("dir", CONFIG["FILES_DIR"])
                os.makedirs(dest_dir, exist_ok=True)
                dest_path = os.path.join(dest_dir, safe_name)
                mode = "ab" if data.get("append") else "w"
                if data.get("append"):
                    with open(dest_path, "ab") as f:
                        f.write(content.encode("utf-8") if isinstance(content, str) else content)
                else:
                    with open(dest_path, "w", encoding="utf-8") as f:
                        f.write(content if isinstance(content, str) else json.dumps(content))
                self._send_json({"status": "written", "file": dest_path})

            elif path == "/listen":
                duration = int(data.get("duration", 5))
                outfile  = data.get("output", os.path.join(CONFIG["FILES_DIR"], "listen_latest.mp3"))
                r = termux_run("termux-microphone-record", "-d", str(duration), "-f", outfile, timeout=duration+15)
                self._send_json({"status": "recorded", "file": outfile, **r})

            elif path == "/conversation":
                # Send a message, get TTS spoken response placeholder
                message = data.get("message", "")
                if not message:
                    self._send_json({"error": "missing 'message' field"}, 400)
                    return
                # Toast acknowledgement + TTS
                termux_run("termux-toast", f"Received: {message[:60]}")
                reply = data.get("reply", f"Got your message: {message[:80]}")
                termux_run("termux-tts-speak", reply, timeout=60)
                self._send_json({"status": "conversed", "message": message, "reply": reply})

            elif path == "/voice":
                # POST a text, return spoken file or just speak it
                text    = data.get("text", "")
                save    = data.get("save", False)
                outfile = os.path.join(CONFIG["FILES_DIR"], "voice_latest.mp3")
                args    = ["termux-tts-speak"]
                if save:
                    args += ["-f", outfile]
                if text:
                    args.append(text)
                    r = termux_run(*args, timeout=60)
                    resp = {"status": "spoken", "text": text, **r}
                    if save and os.path.isfile(outfile):
                        resp["file"] = outfile
                    self._send_json(resp)
                else:
                    self._send_json({"error": "missing 'text' field"}, 400)

            else:
                self._send_json({"error": "not found", "path": path}, 404)

        except subprocess.TimeoutExpired:
            self._send_json({"error": "command timed out"}, 504)
        except Exception as e:
            self._handle_exception(e)

    def _handle_exception(self, e: Exception):
        tb = traceback.format_exc()
        log.error(tb)
        msg = f"Bridge exception on {CONFIG['DEVICE_ID']}: {e}\n{tb[:300]}"
        threading.Thread(target=ntfy_alert, args=("Bridge Error", msg), daemon=True).start()
        self._send_json({"error": str(e), "type": type(e).__name__}, 500)


# ─── SERVER RUNNER WITH AUTO-RECONNECT ────────────────────────────────────────
_restart_count = 0
_shutdown_flag  = threading.Event()

def run_server():
    global _restart_count
    while not _shutdown_flag.is_set():
        try:
            server = HTTPServer(("0.0.0.0", CONFIG["PORT"]), BridgeHandler)
            server.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            log.info(f"[Bridge] Listening on 0.0.0.0:{CONFIG['PORT']}")
            _restart_count = 0
            server.serve_forever()
        except OSError as e:
            _restart_count += 1
            log.error(f"[Bridge] OSError (attempt {_restart_count}): {e}")
            if _restart_count >= CONFIG["MAX_RESTARTS"]:
                ntfy_alert("Bridge FATAL", f"{CONFIG['DEVICE_ID']}: server failed {_restart_count}x. Needs manual intervention.", priority="urgent")
                log.critical("[Bridge] Max restarts exceeded. Giving up.")
                os._exit(1)
            ntfy_alert("Bridge Restarting", f"{CONFIG['DEVICE_ID']}: server restarting (attempt {_restart_count})")
            time.sleep(CONFIG["RESTART_DELAY"] * _restart_count)
        except Exception as e:
            log.error(f"[Bridge] Unexpected error: {e}\n{traceback.format_exc()}")
            time.sleep(CONFIG["RESTART_DELAY"])


# ─── STATE HEARTBEAT ──────────────────────────────────────────────────────────
def state_heartbeat():
    """Push device state to Supabase every 5 minutes."""
    while not _shutdown_flag.is_set():
        try:
            push_state()
        except Exception as e:
            log.warning(f"[heartbeat] {e}")
        _shutdown_flag.wait(300)


# ─── GRACEFUL SHUTDOWN ────────────────────────────────────────────────────────
def _handle_signal(signum, frame):
    log.info(f"[Bridge] Signal {signum} received — shutting down.")
    _shutdown_flag.set()
    sys.exit(0)

signal.signal(signal.SIGTERM, _handle_signal)
signal.signal(signal.SIGINT,  _handle_signal)


# ─── MAIN ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    log.info(f"[Bridge] Starting TCC Bridge {CONFIG['VERSION']} on {CONFIG['DEVICE_ID']}")
    os.makedirs(CONFIG["FILES_DIR"], exist_ok=True)

    # Boot alert
    threading.Thread(
        target=ntfy_alert,
        args=("Bridge Online", f"TCC Bridge V2 ONLINE on {CONFIG['DEVICE_ID']}"),
        kwargs={"tags": "rocket,robot", "priority": "default"},
        daemon=True,
    ).start()

    # Initial state push
    threading.Thread(target=push_state, daemon=True).start()

    # Heartbeat thread
    threading.Thread(target=state_heartbeat, daemon=True).start()

    # Server (blocking call with internal reconnect)
    run_server()
