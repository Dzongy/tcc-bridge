#!/usr/bin/env python3
"""
TCC Bridge V2.5 - BULLETPROOF EDITION
Built by KAEL God Builder for Commander.
Features: Auto-reconnect, Health endpoint, State push, PM2, Termux:Boot.
"""

import os, json, time, threading, subprocess, logging, traceback, socket
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

# CONFIG
SUPABASE_URL = "https://vbqbbziqleymxcyesmky.supabase.co"
SUPABASE_KEY = "sb_secret_lIbl-DBgdnrt_fejgJjKqg_qR62SVEm"
NTFY_TOPIC = "tcc-zenith-hive"
PORT = 8765
REPORT_SEC = 300
DEVICE_ID = "zenith-phone"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(os.path.expanduser("~/tcc-bridge.log")),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("BridgeV2")

class BridgeHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({
                "status": "ok",
                "device": DEVICE_ID,
                "uptime": time.time() - START_TIME,
                "timestamp": time.time()
            }).encode())
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        try:
            payload = json.loads(post_data.decode('utf-8'))
            action = payload.get("action")
            logger.info(f"Action received: {action}")
            
            result = {"status": "success"}
            if action == "exec":
                cmd = payload.get("command")
                res = subprocess.check_output(cmd, shell=True).decode()
                result["output"] = res
            elif action == "toast":
                msg = payload.get("message")
                subprocess.run(f"termux-toast '{msg}'", shell=True)
            elif action == "speak":
                msg = payload.get("message")
                subprocess.run(f"termux-tts-speak '{msg}'", shell=True)
            elif action == "vibrate":
                subprocess.run("termux-vibrate", shell=True)
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(result).encode())
        except Exception as e:
            logger.error(f"Error handling POST: {e}")
            self.send_response(500)
            self.end_headers()
            self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode())

def push_state():
    while True:
        try:
            # Get battery status
            bat = json.loads(subprocess.check_output("termux-battery-status", shell=True).decode())
            state = {
                "device_id": DEVICE_ID,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "battery_level": bat.get("percentage"),
                "is_charging": bat.get("status") == "CHARGING",
                "status": "online",
                "uptime": time.time() - START_TIME
            }
            
            # Push to Supabase device_state
            req = Request(f"{SUPABASE_URL}/rest/v1/device_state", 
                          data=json.dumps(state).encode(),
                          headers={
                              "apikey": SUPABASE_KEY,
                              "Authorization": f"Bearer {SUPABASE_KEY}",
                              "Content-Type": "application/json",
                              "Prefer": "resolution=merge-duplicates"
                          })
            urlopen(req, timeout=10)
            logger.info("State pushed to Supabase")
        except Exception as e:
            logger.error(f"State push failed: {e}")
        time.sleep(REPORT_SEC)

def watchdog():
    """Checks tunnel and ntfy if down"""
    while True:
        try:
            # Simple check if zenith.cosmic-claw.com/health is reachable
            # (Requires the tunnel to be up)
            req = Request("https://zenith.cosmic-claw.com/health")
            with urlopen(req, timeout=10) as response:
                if response.status != 200:
                    raise Exception(f"HTTP {response.status}")
            logger.info("Health check passed")
        except Exception as e:
            logger.warning(f"Health check failed: {e}")
            # Alert via ntfy
            try:
                alert = f"⚠️ BRIDGE ALERT: Tunnel or server down on {DEVICE_ID}. Error: {e}"
                req = Request(f"https://ntfy.sh/{NTFY_TOPIC}", data=alert.encode())
                urlopen(req)
            except: pass
        time.sleep(600) # Check every 10 mins

if __name__ == "__main__":
    from datetime import datetime, timezone
    START_TIME = time.time()
    logger.info(f"Starting Bridge V2.5 on port {PORT}...")
    
    # Start threads
    threading.Thread(target=push_state, daemon=True).start()
    threading.Thread(target=watchdog, daemon=True).start()
    
    server = HTTPServer(('0.0.0.0', PORT), BridgeHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()
