#!/usr/bin/env python3
"""
TCC Bridge V5.0 â THE BULLETPROOF BRIDGE
Built by KAEL God Builder for Commander.
Features: Health checks, Termux integration, robust command execution, 
internal heartbeat thread to Supabase & ntfy.
"""
import os, sys, json, time, logging, subprocess, threading, socket
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

# CONFIG
PORT = int(os.environ.get("BRIDGE_PORT", "8765"))
AUTH_TOKEN = os.environ.get("BRIDGE_AUTH", "amos-bridge-2026")
DEVICE_ID = "amos-arms"
SUPABASE_URL = "https://vbqbbziqleymxcyesmky.supabase.co/rest/v1/device_state"
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "") # Should be set in env
NTFY_URL = "https://ntfy.sh/tcc-zenith-hive"

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
log = logging.getLogger("bridge")

class BridgeHandler(BaseHTTPRequestHandler):
    def check_auth(self):
        auth = self.headers.get('Authorization')
        if auth == f"Bearer {AUTH_TOKEN}":
            return True
        self.send_error(401, "Unauthorized")
        return False

    def do_GET(self):
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "alive", "device": DEVICE_ID, "time": time.time()}).encode())
        else:
            self.send_error(404)

    def do_POST(self):
        if not self.check_auth(): return
        
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode()
        try:
            data = json.loads(body)
        except:
            self.send_error(400, "Invalid JSON")
            return

        path = self.path
        res = {"status": "ok"}
        
        try:
            if path == '/exec':
                cmd = data.get("command")
                log.info(f"Executing: {cmd}")
                output = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT).decode()
                res["output"] = output
            elif path == '/toast':
                msg = data.get("message", "Bridge Active")
                subprocess.run(f"termux-toast '{msg}'", shell=True)
            elif path == '/vibrate':
                dur = data.get("duration", 500)
                subprocess.run(f"termux-vibrate -d {dur}", shell=True)
            elif path == '/speak':
                msg = data.get("message", "Hello Commander")
                subprocess.run(f"termux-tts-speak '{msg}'", shell=True)
            elif path == '/push_state':
                # Manual trigger for state push
                threading.Thread(target=report_state, args=(True,)).start()
                res["message"] = "State push triggered"
            else:
                self.send_error(404)
                return
        except Exception as e:
            res = {"status": "error", "message": str(e)}

        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(res).encode())

def report_state(manual=False):
    """Internal reporting to Supabase and ntfy"""
    try:
        # Gather stats
        battery = subprocess.check_output("termux-battery-status", shell=True).decode()
        bat_data = json.loads(battery)
        
        payload = {
            "device_id": DEVICE_ID,
            "battery": int(bat_data.get("percentage", 0)),
            "network": "connected",
            "hostname": socket.gethostname(),
            "raw_output": f"Manual: {manual} | Battery: {bat_data.get('percentage')}% | Status: {bat_data.get('status')}"
        }
        
        # Supabase Push
        if SUPABASE_KEY:
            req = Request(SUPABASE_URL, data=json.dumps(payload).encode(), method="POST")
            req.add_header("apikey", SUPABASE_KEY)
            req.add_header("Authorization", f"Bearer {SUPABASE_KEY}")
            req.add_header("Content-Type", "application/json")
            req.add_header("Prefer", "return=minimal")
            with urlopen(req) as response:
                pass
        
        # ntfy Heartbeat (only if manual or every hour)
        if manual:
            req_ntfy = Request(NTFY_URL, data=f"Bridge V5.0 Heartbeat: {DEVICE_ID} is ALIVE. Battery: {bat_data.get('percentage')}%".encode())
            req_ntfy.add_header("Title", "Bridge Heartbeat")
            req_ntfy.add_header("Tags", "robot,check")
            with urlopen(req_ntfy) as response:
                pass
                
    except Exception as e:
        log.error(f"Reporting failed: {e}")

def heartbeat_loop():
    while True:
        report_state()
        time.sleep(3600) # Every hour

def run_server():
    server = HTTPServer(('0.0.0.0', PORT), BridgeHandler)
    log.info(f"Bridge V5.0 starting on port {PORT}...")
    threading.Thread(target=heartbeat_loop, daemon=True).start()
    server.serve_forever()

if __name__ == "__main__":
    run_server()
