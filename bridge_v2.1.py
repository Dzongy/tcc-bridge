#!/usr/bin/env python3
"""
TCC Bridge V2.1.0 - "Kael Edition"
Bulletproof Bridge for Termux/Android
Features: Supabase Heartbeat, ntfy Alerts, Mobile API (termux-api)
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

# --- CONFIG ---
SUPABASE_URL  = "https://vbqbbziqleymxcyesmky.supabase.co"
SUPABASE_KEY  = "sb_secret_lIbl-DBgdnrt_fejgJjKqg_qR62SVEm" # Service role or public? Assuming service role for state push
NTFY_TOPIC    = "tcc-zenith-hive"
SERVER_PORT   = 8080 # Changed to 8080 to match previous bridge v1 standard or user preference
LOG_FILE      = os.path.expanduser("~/tcc-bridge.log")
HEARTBEAT_IV  = 300  # 5 minutes as requested by state-push.py logic or every minute for higher resolution?
DEVICE_ID     = "Commander-Samsung"

# --- LOGGING ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("BridgeV2")

def run_cmd(cmd):
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return result.stdout.strip()
    except Exception as e:
        return str(e)

def ntfy_alert(message, priority=3, tags=["robot"]):
    try:
        req = Request(f"https://ntfy.sh/{NTFY_TOPIC}", data=message.encode('utf-8'))
        req.add_header("Title", "Bridge Status Update")
        req.add_header("Priority", str(priority))
        req.add_header("Tags", ",".join(tags))
        urlopen(req)
    except Exception as e:
        logger.error(f"ntfy alert failed: {e}")

def supabase_push(data):
    try:
        payload = json.dumps({
            "device_id": DEVICE_ID,
            "status": "online",
            "last_seen": datetime.now(timezone.utc).isoformat(),
            "data": data
        }).encode('utf-8')
        
        # Using a table like 'device_state' or 'kael_memory'? 
        # System prompt says: family_members, device_state, kael_memory, operations_log, zenith_messages
        url = f"{SUPABASE_URL}/rest/v1/device_state"
        req = Request(url, data=payload, method='POST')
        req.add_header("apikey", SUPABASE_KEY)
        req.add_header("Authorization", f"Bearer {SUPABASE_KEY}")
        req.add_header("Content-Type", "application/json")
        req.add_header("Prefer", "resolution=merge-duplicates")
        
        with urlopen(req) as response:
            return response.read()
    except Exception as e:
        logger.error(f"Supabase push failed: {e}")
        return None

class BridgeHandler(BaseHTTPRequestHandler):
    def _send_resp(self, code, data):
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))

    def do_GET(self):
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        
        if path == '/health':
            self._send_resp(200, {"status": "ok", "time": time.time(), "device": DEVICE_ID})
        elif path == '/status':
            stats = {
                "uptime": run_cmd("uptime"),
                "battery": run_cmd("termux-battery-status"),
                "memory": run_cmd("free -m"),
                "bridge_version": "2.1.0"
            }
            self._send_resp(200, stats)
        else:
            self._send_resp(404, {"error": "not found"})

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length).decode('utf-8')
        try:
            body = json.loads(post_data) if post_data else {}
        except:
            body = {}
            
        parsed_path = urlparse(self.path)
        path = parsed_path.path

        if path == '/exec':
            cmd = body.get('cmd')
            if cmd:
                res = run_cmd(cmd)
                self._send_resp(200, {"output": res})
            else:
                self._send_resp(400, {"error": "no cmd provided"})
        
        elif path == '/toast':
            msg = body.get('message', 'Hello from Bridge')
            run_cmd(f'termux-toast "{msg}"')
            self._send_resp(200, {"status": "sent"})
            
        elif path == '/speak':
            msg = body.get('message', 'Hello')
            run_cmd(f'termux-tts-speak "{msg}"')
            self._send_resp(200, {"status": "speaking"})

        elif path == '/vibrate':
            duration = body.get('duration', 500)
            run_cmd(f'termux-vibrate -d {duration}')
            self._send_resp(200, {"status": "vibrating"})
            
        elif path == '/ntfy':
            msg = body.get('message', '')
            ntfy_alert(msg)
            self._send_resp(200, {"status": "dispatched"})

        else:
            self._send_resp(404, {"error": "not found"})

def heartbeat_loop():
    logger.info("Heartbeat thread started")
    while True:
        try:
            batt = json.loads(run_cmd("termux-battery-status") or "{}")
            state = {
                "battery_level": batt.get("percentage"),
                "is_charging": batt.get("status") == "charging",
                "uptime_secs": time.time() - start_time
            }
            supabase_push(state)
        except Exception as e:
            logger.error(f"Heartbeat error: {e}")
        time.sleep(60)

start_time = time.time()

if __name__ == "__main__":
    logger.info(f"Starting TCC Bridge V2.1.0 on port {SERVER_PORT}...")
    
    # Start Heartbeat
    hb_thread = threading.Thread(target=heartbeat_loop, daemon=True)
    hb_thread.start()
    
    # Initial ntfy notification
    ntfy_alert(f"Bridge V2.1.0 Online - {DEVICE_ID}", priority=4, tags=["rocket", "check"])
    
    server = HTTPServer(('0.0.0.0', SERVER_PORT), BridgeHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    server.server_close()
    logger.info("Bridge stopped")
