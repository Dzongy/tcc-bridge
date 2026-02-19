#!/usr/bin/env python3
# =============================================================================
# TCC Bridge - Bulletproof V2
# God-tier resilience. Zero excuses.
# =============================================================================

import os
import sys
import json
import time
import signal
import socket
import logging
import platform
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from datetime import datetime, timezone
from functools import wraps

# --- Optional imports with graceful fallback ---
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

try:
    import urllib.request
    import urllib.parse
    import urllib.error
except ImportError:
    pass

# =============================================================================
# CONFIG
# =============================================================================
PORT = int(os.environ.get('BRIDGE_PORT', 8080))
BRIDGE_AUTH = os.environ.get('BRIDGE_AUTH', '')
SUPABASE_URL = os.environ.get('SUPABASE_URL', 'https://vbqbbziqleymxcyesmky.supabase.co')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY', '')
NTFY_OPS_TOPIC = os.environ.get('NTFY_OPS_TOPIC', 'zenith-escape')
NTFY_HIVE_TOPIC = os.environ.get('NTFY_HIVE_TOPIC', 'tcc-zenith-hive')
NTFY_BASE = 'https://ntfy.sh'
HEARTBEAT_INTERVAL = int(os.environ.get('HEARTBEAT_INTERVAL', 30))
START_TIME = time.time()

# =============================================================================
# LOGGING
# =============================================================================
log_dir = os.path.expanduser('~/tcc')
os.makedirs(log_dir, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(log_dir, 'bridge.log')),
        logging.StreamHandler(sys.stdout)
    ]
)
log = logging.getLogger('TCC-Bridge')

# =============================================================================
# UTILITIES
# =============================================================================

def safe_run(cmd, timeout=15, shell=True):
    """Run a shell command safely. Returns (stdout, stderr, returncode)."""
    try:
        result = subprocess.run(
            cmd,
            shell=shell,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return result.stdout.strip(), result.stderr.strip(), result.returncode
    except subprocess.TimeoutExpired:
        log.warning(f'Command timed out: {cmd}')
        return '', 'TIMEOUT', -1
    except Exception as e:
        log.error(f'Command error [{cmd}]: {e}')
        return '', str(e), -1


def kill_port(port):
    """Nuke anything sitting on our port. No mercy."""
    log.info(f'Clearing port {port}...')
    out, _, _ = safe_run(f'lsof -ti :{port}')
    if out:
        pids = out.split()
        for pid in pids:
            safe_run(f'kill -9 {pid}')
            log.info(f'Killed PID {pid} on port {port}')
        time.sleep(1)
    else:
        log.info(f'Port {port} is clear.')


def http_post(url, data, headers=None, timeout=10):
    """Generic HTTP POST. Returns (response_text, status_code)."""
    try:
        if isinstance(data, dict):
            data = json.dumps(data).encode('utf-8')
        elif isinstance(data, str):
            data = data.encode('utf-8')
        req = urllib.request.Request(url, data=data, method='POST')
        req.add_header('Content-Type', 'application/json')
        if headers:
            for k, v in headers.items():
                req.add_header(k, v)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode('utf-8'), resp.status
    except urllib.error.HTTPError as e:
        log.warning(f'HTTP POST error {url}: {e.code} {e.reason}')
        return '', e.code
    except Exception as e:
        log.error(f'HTTP POST failed {url}: {e}')
        return '', -1


def http_get(url, headers=None, timeout=10):
    """Generic HTTP GET. Returns (response_text, status_code)."""
    try:
        req = urllib.request.Request(url)
        if headers:
            for k, v in headers.items():
                req.add_header(k, v)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode('utf-8'), resp.status
    except Exception as e:
        log.error(f'HTTP GET failed {url}: {e}')
        return '', -1


def ntfy_push(topic, message, title='TCC Bridge', priority='default', tags=None):
    """Push a notification to ntfy.sh."""
    if not topic:
        return
    url = f'{NTFY_BASE}/{topic}'
    headers = {
        'Title': title,
        'Priority': priority,
    }
    if tags:
        headers['Tags'] = ','.join(tags)
    try:
        req = urllib.request.Request(url, data=message.encode('utf-8'), method='POST')
        for k, v in headers.items():
            req.add_header(k, v)
        with urllib.request.urlopen(req, timeout=8) as resp:
            log.info(f'ntfy push OK -> {topic}')
            return resp.status
    except Exception as e:
        log.warning(f'ntfy push failed [{topic}]: {e}')
        return -1


def supabase_upsert(table, payload):
    """Upsert a record into Supabase."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        log.warning('Supabase not configured, skipping upsert.')
        return
    url = f'{SUPABASE_URL}/rest/v1/{table}'
    headers = {
        'apikey': SUPABASE_KEY,
        'Authorization': f'Bearer {SUPABASE_KEY}',
        'Prefer': 'resolution=merge-duplicates',
    }
    _, status = http_post(url, payload, headers=headers)
    if status in (200, 201):
        log.info(f'Supabase upsert OK -> {table}')
    else:
        log.warning(f'Supabase upsert failed -> {table} (status {status})')


def get_battery_info():
    """Get battery status via Termux API or /sys."""
    try:
        out, _, rc = safe_run('termux-battery-status', timeout=5)
        if rc == 0 and out:
            return json.loads(out)
    except Exception:
        pass
    # Fallback: read /sys
    try:
        capacity_path = '/sys/class/power_supply/battery/capacity'
        status_path = '/sys/class/power_supply/battery/status'
        cap = open(capacity_path).read().strip() if os.path.exists(capacity_path) else 'unknown'
        status = open(status_path).read().strip() if os.path.exists(status_path) else 'unknown'
        return {'percentage': cap, 'status': status}
    except Exception:
        return {'percentage': 'unknown', 'status': 'unknown'}


def get_memory_info():
    """Get memory info."""
    if HAS_PSUTIL:
        try:
            vm = psutil.virtual_memory()
            return {
                'total_mb': round(vm.total / 1024 / 1024, 1),
                'available_mb': round(vm.available / 1024 / 1024, 1),
                'used_percent': vm.percent
            }
        except Exception:
            pass
    # Fallback: /proc/meminfo
    try:
        mem = {}
        with open('/proc/meminfo') as f:
            for line in f:
                parts = line.split()
                if parts[0] in ('MemTotal:', 'MemAvailable:', 'MemFree:'):
                    mem[parts[0].rstrip(':')] = int(parts[1]) // 1024
        total = mem.get('MemTotal', 0)
        avail = mem.get('MemAvailable', mem.get('MemFree', 0))
        used_pct = round((1 - avail / total) * 100, 1) if total else 0
        return {'total_mb': total, 'available_mb': avail, 'used_percent': used_pct}
    except Exception:
        return {'total_mb': 0, 'available_mb': 0, 'used_percent': 0}


def get_uptime():
    """Get bridge uptime in seconds."""
    return round(time.time() - START_TIME, 1)


def build_health_payload():
    """Construct the full health payload."""
    return {
        'id': 'zenith-primary',
        'status': 'online',
        'uptime_seconds': get_uptime(),
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'hostname': socket.gethostname(),
        'platform': platform.system(),
        'battery': get_battery_info(),
        'memory': get_memory_info(),
        'port': PORT,
        'version': 'v2.0.0-bulletproof'
    }

# =============================================================================
# AUTH DECORATOR
# =============================================================================

def require_auth(handler_method):
    """Decorator to enforce bearer token auth on handler methods."""
    @wraps(handler_method)
    def wrapper(self, *args, **kwargs):
        if BRIDGE_AUTH:
            auth_header = self.headers.get('Authorization', '')
            expected = f'Bearer {BRIDGE_AUTH}'
            if auth_header != expected:
                self.send_json({'error': 'Unauthorized'}, status=401)
                log.warning(f'Unauthorized request from {self.client_address[0]}')
                return
        return handler_method(self, *args, **kwargs)
    return wrapper

# =============================================================================
# REQUEST HANDLER
# =============================================================================

class BridgeHandler(BaseHTTPRequestHandler):

    def log_message(self, format, *args):
        log.info(f'REQUEST {self.address_string()} - {format % args}')

    def send_json(self, payload, status=200):
        body = json.dumps(payload, indent=2).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(body)

    def read_json_body(self):
        try:
            length = int(self.headers.get('Content-Length', 0))
            if length == 0:
                return {}
            raw = self.rfile.read(length)
            return json.loads(raw.decode('utf-8'))
        except Exception as e:
            log.error(f'Failed to parse JSON body: {e}')
            return {}

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Authorization, Content-Type')
        self.end_headers()

    def do_GET(self):
        path = self.path.split('?')[0]
        if path == '/health':
            self.handle_health()
        else:
            self.send_json({'error': 'Not Found'}, status=404)

    def do_POST(self):
        path = self.path.split('?')[0]
        routes = {
            '/exec': self.handle_exec,
            '/toast': self.handle_toast,
            '/speak': self.handle_speak,
            '/vibrate': self.handle_vibrate,
            '/write_file': self.handle_write_file,
            '/listen': self.handle_listen,
            '/voice': self.handle_voice,
        }
        handler = routes.get(path)
        if handler:
            handler()
        else:
            self.send_json({'error': 'Not Found'}, status=404)

    # -------------------------------------------------------------------------
    # ENDPOINTS
    # -------------------------------------------------------------------------

    def handle_health(self):
        payload = build_health_payload()
        self.send_json(payload)

    @require_auth
    def handle_exec(self):
        body = self.read_json_body()
        cmd = body.get('cmd', '').strip()
        if not cmd:
            self.send_json({'error': 'cmd is required'}, status=400)
            return
        timeout = int(body.get('timeout', 30))
        log.info(f'Executing command: {cmd}')
        stdout, stderr, rc = safe_run(cmd, timeout=timeout)
        self.send_json({
            'stdout': stdout,
            'stderr': stderr,
            'returncode': rc
        })

    @require_auth
    def handle_toast(self):
        body = self.read_json_body()
        message = body.get('message', '').strip()
        if not message:
            self.send_json({'error': 'message is required'}, status=400)
            return
        out, err, rc = safe_run(f'termux-toast -s "{message}"')
        self.send_json({'ok': rc == 0, 'stderr': err})

    @require_auth
    def handle_speak(self):
        body = self.read_json_body()
        text = body.get('text', '').strip()
        if not text:
            self.send_json({'error': 'text is required'}, status=400)
            return
        lang = body.get('lang', 'en')
        rate = body.get('rate', 1.0)
        out, err, rc = safe_run(f'termux-tts-speak -l {lang} -r {rate} "{text}"')
        self.send_json({'ok': rc == 0, 'stderr': err})

    @require_auth
    def handle_vibrate(self):
        body = self.read_json_body()
        duration = int(body.get('duration', 500))
        out, err, rc = safe_run(f'termux-vibrate -d {duration}')
        self.send_json({'ok': rc == 0, 'stderr': err})

    @require_auth
    def handle_write_file(self):
        body = self.read_json_body()
        path = body.get('path', '').strip()
        content = body.get('content', '')
        if not path:
            self.send_json({'error': 'path is required'}, status=400)
            return
        try:
            full_path = os.path.expanduser(path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, 'w') as f:
                f.write(content)
            log.info(f'File written: {full_path}')
            self.send_json({'ok': True, 'path': full_path})
        except Exception as e:
            log.error(f'write_file error: {e}')
            self.send_json({'error': str(e)}, status=500)

    @require_auth
    def handle_listen(self):
        body = self.read_json_body()
        duration = int(body.get('duration', 5))
        output_file = body.get('output', '~/tcc/recording.mp4')
        output_file = os.path.expanduser(output_file)
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        out, err, rc = safe_run(
            f'termux-microphone-record -l {duration} -f {output_file}',
            timeout=duration + 10
        )
        self.send_json({'ok': rc == 0, 'file': output_file, 'stderr': err})

    @require_auth
    def handle_voice(self):
        """Record audio and transcribe via Whisper or similar."""
        body = self.read_json_body()
        duration = int(body.get('duration', 5))
        tmp_file = os.path.expanduser('~/tcc/voice_stt.mp4')
        os.makedirs(os.path.dirname(tmp_file), exist_ok=True)
        # Record
        _, err_rec, rc_rec = safe_run(
            f'termux-microphone-record -l {duration} -f {tmp_file}',
            timeout=duration + 10
        )
        if rc_rec != 0:
            self.send_json({'error': 'Recording failed', 'stderr': err_rec}, status=500)
            return
        # Transcribe
        whisper_cmd = f'whisper {tmp_file} --model tiny --output_format txt 2>/dev/null'
        out_txt, err_txt, rc_txt = safe_run(whisper_cmd, timeout=60)
        # Try to read txt output
        txt_file = tmp_file.replace('.mp4', '.txt')
        transcript = ''
        if os.path.exists(txt_file):
            with open(txt_file) as f:
                transcript = f.read().strip()
        elif out_txt:
            transcript = out_txt
        self.send_json({'ok': True, 'transcript': transcript, 'raw': out_txt})

# =============================================================================
# HEARTBEAT
# =============================================================================

def heartbeat_loop():
    """Periodically push health to Supabase and ntfy."""
    # Give the server a moment to boot
    time.sleep(5)
    log.info('Heartbeat loop started.')
    while True:
        try:
            payload = build_health_payload()
            # Push to Supabase
            supabase_upsert('bridge_status', payload)
            # Push summary to ntfy ops
            bat = payload['battery']
            mem = payload['memory']
            uptime_min = round(payload['uptime_seconds'] / 60, 1)
            msg = (
                f'[ZENITH ONLINE] Uptime: {uptime_min}m | '
                f'Battery: {bat.get("percentage", "?")}% {bat.get("status", "")} | '
                f'RAM: {mem.get("used_percent", "?")}% used'
            )
            ntfy_push(NTFY_OPS_TOPIC, msg, title='TCC Heartbeat', tags=['heart', 'green_circle'])
        except Exception as e:
            log.error(f'Heartbeat error: {e}')
        time.sleep(HEARTBEAT_INTERVAL)

# =============================================================================
# STARTUP BANNER
# =============================================================================

def print_banner():
    banner = """
 ████████╗ ██████╗ ██████╗
    ██╔══╝██╔════╝██╔════╝
    ██║   ██║     ██║
    ██║   ██║     ██║
    ██║   ╚██████╗╚██████╗
    ╚═╝    ╚═════╝ ╚═════╝
  BRIDGE V2 - BULLETPROOF
    """
    print(banner)
    log.info(f'TCC Bridge V2 starting on port {PORT}')
    log.info(f'Auth: {"ENABLED" if BRIDGE_AUTH else "DISABLED (WARNING)"}')
    log.info(f'Supabase: {SUPABASE_URL}')
    log.info(f'ntfy ops: {NTFY_OPS_TOPIC} | hive: {NTFY_HIVE_TOPIC}')

# =============================================================================
# MAIN
# =============================================================================

def main():
    print_banner()

    # Ensure port is free
    kill_port(PORT)

    # Announce startup
    ntfy_push(
        NTFY_OPS_TOPIC,
        f'TCC Bridge V2 is ONLINE on port {PORT}. Timestamp: {datetime.now(timezone.utc).isoformat()}',
        title='BRIDGE ONLINE',
        priority='high',
        tags=['rocket', 'white_check_mark']
    )

    # Start heartbeat in background
    hb_thread = threading.Thread(target=heartbeat_loop, daemon=True)
    hb_thread.start()

    # Graceful shutdown
    def shutdown(sig, frame):
        log.info('Shutdown signal received. Goodbye, Commander.')
        ntfy_push(NTFY_OPS_TOPIC, 'TCC Bridge is going OFFLINE.', title='BRIDGE OFFLINE', priority='high', tags=['warning'])
        sys.exit(0)

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)

    # Start server
    server = HTTPServer(('0.0.0.0', PORT), BridgeHandler)
    log.info(f'Server listening on 0.0.0.0:{PORT}')
    try:
        server.serve_forever()
    except Exception as e:
        log.critical(f'Server crashed: {e}')
        ntfy_push(NTFY_OPS_TOPIC, f'BRIDGE CRASHED: {e}', title='BRIDGE CRASH', priority='urgent', tags=['skull'])
        sys.exit(1)


if __name__ == '__main__':
    main()
