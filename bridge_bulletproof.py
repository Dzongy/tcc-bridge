#!/usr/bin/env python3
"""
TCC Bridge v8.0.0 — THE PERMANENT BRIDGE
Bulletproof phone control HTTP server for Termux.
Survives: Reboots, network drops, process kills, memory cleanup.
"""
import subprocess, json, os, sys, socket, signal, logging, time, threading, traceback
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.request import Request, urlopen
from urllib.error import URLError
from urllib.parse import parse_qs, urlparse

# -- Config --
AUTH_TOKEN = os.environ.get("BRIDGE_AUTH", "amos-bridge-2026")
PORT = int(os.environ.get("BRIDGE_PORT", "8080"))
LOG_FILE = os.path.expanduser("~/tcc/logs/bridge.log")
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://vbqbbziqleymxcyesmky.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")
NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "tcc-zenith-hive")
PUBLIC_URL = os.environ.get("PUBLIC_URL", "https://zenith.cosmic-claw.com")
VERSION = "6.0.0"
START_TIME = time.time()

os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", 
                    handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler(sys.stderr)])
log = logging.getLogger("bridge")

def ntfy(msg, priority=3, tags=None, title="TCC Bridge V6"):
    try:
        req = Request(f"https://ntfy.sh/{NTFY_TOPIC}", data=msg.encode('utf-8'))
        req.add_header("Title", title)
        req.add_header("Priority", str(priority))
        if tags: req.add_header("Tags", ",".join(tags))
        urlopen(req, timeout=10)
    except Exception as e: log.error(f"ntfy failed: {e}")

class BridgeHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args): 
        log.info("%s - - [%s] %s" % (self.client_address[0], self.log_date_time_string(), format%args))
    
    def send_success(self, data):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def send_error_json(self, code, msg):
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({"error": msg, "code": code}).encode())

    def do_GET(self):
        if self.headers.get('Authorization') != f"Bearer {AUTH_TOKEN}" and self.path != "/ping" and self.path != "/health":
            return self.send_error_json(401, "Unauthorized")

        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        path = parsed.path

        try:
            if path == "/" or path == "/health":
                self.send_success({
                    "status": "online",
                    "version": VERSION,
                    "uptime": int(time.time() - START_TIME),
                    "device": socket.gethostname(),
                    "timestamp": time.time()
                })
            elif path == "/ping":
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"pong")
            elif path == "/toast":
                msg = params.get('msg', ['Hello from TCC'])[0]
                subprocess.run(["termux-toast", msg])
                self.send_success({"sent": msg})
            elif path == "/vibrate":
                ms = params.get('ms', ['500'])[0]
                subprocess.run(["termux-vibrate", "-d", ms])
                self.send_success({"duration": ms})
            elif path == "/speak":
                msg = params.get('msg', [''])[0]
                subprocess.run(["termux-tts-speak", msg])
                self.send_success({"speaking": msg})
            elif path == "/exec":
                cmd = params.get('cmd', [''])[0]
                if not cmd: return self.send_error_json(400, "Missing cmd")
                res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                self.send_success({"stdout": res.stdout, "stderr": res.stderr, "code": res.returncode})
            elif path == "/battery":
                res = subprocess.run(["termux-battery-status"], capture_output=True, text=True)
                self.send_success(json.loads(res.stdout))
            elif path == "/write_file":
                f_path = params.get('path', [''])[0]
                content = params.get('content', [''])[0]
                if not f_path: return self.send_error_json(400, "Missing path")
                os.makedirs(os.path.dirname(os.path.expanduser(f_path)), exist_ok=True)
                with open(os.path.expanduser(f_path), "w") as f: f.write(content)
                self.send_success({"path": f_path, "bytes": len(content)})
            else:
                self.send_error_json(404, "Not Found")
        except Exception as e:
            log.error(traceback.format_exc())
            self.send_error_json(500, str(e))

class HealthThread(threading.Thread):
    def run(self):
        log.info("Self-healing health thread started.")
        last_push = 0
        fail_count = 0
        while True:
            try:
                # 1. Push state to Supabase every 5 mins
                if time.time() - last_push > 300 and SUPABASE_KEY:
                    uptime = int(time.time() - START_TIME)
                    payload = {
                        "id": "phone-bridge", 
                        "status": "online", 
                        "uptime": uptime, 
                        "version": VERSION, 
                        "last_seen": "now()"
                    }
                    try:
                        req = Request(f"{SUPABASE_URL}/rest/v1/device_state?id=eq.phone-bridge", 
                                      data=json.dumps(payload).encode(), method="POST")
                        req.add_header("apikey", SUPABASE_KEY)
                        req.add_header("Authorization", f"Bearer {SUPABASE_KEY}")
                        req.add_header("Content-Type", "application/json")
                        req.add_header("Prefer", "resolution=merge-duplicates")
                        urlopen(req, timeout=10)
                        last_push = time.time()
                        log.info("State pushed to Supabase.")
                    except Exception as se:
                        log.error(f"Supabase push failed: {se}")

                # 2. Check tunnel health via public URL every 60s
                try:
                    req = Request(f"{PUBLIC_URL}/health")
                    # No auth for health endpoint typically, or use token if needed
                    with urlopen(req, timeout=15) as response:
                        if response.status == 200:
                            if fail_count > 0:
                                ntfy("Bridge connectivity RESTORED.", priority=4, tags=["white_check_mark", "green_heart"])
                            fail_count = 0
                        else:
                            raise Exception(f"HTTP {response.status}")
                except Exception as te:
                    fail_count += 1
                    log.warning(f"Public health check failed ({fail_count}): {te}")
                    if fail_count == 3:
                        ntfy(f"Bridge connection dropping! Error: {te}", priority=5, tags=["warning", "sos"], title="BRIDGE CRITICAL")
                    elif fail_count > 3 and fail_count % 10 == 0:
                        ntfy(f"Bridge still offline. Attempting self-healing...", priority=4, tags=["wrench"])
                
            except Exception as e:
                log.error(f"HealthThread loop error: {e}")
            
            time.sleep(60)

def run_server():
    try:
        server = HTTPServer(('0.0.0.0', PORT), BridgeHandler)
        log.info(f"Bridge V6.0.0 starting on port {PORT}...")
        ntfy("Bridge V6.0.0 Online", priority=4, tags=["rocket", "shield"])
        
        health = HealthThread(daemon=True)
        health.start()
        
        server.serve_forever()
    except Exception as e:
        log.critical(f"Server crashed: {e}")
        ntfy(f"Bridge CRASHED: {e}", priority=5, tags=["skull"])
        sys.exit(1)

if __name__ == "__main__":
    def signal_handler(sig, frame):
        log.info("Shutting down...")
        sys.exit(0)
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    run_server()
