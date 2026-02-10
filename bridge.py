#!/usr/bin/env python3
"""AMOS Bridge v2.5 - Phone Control HTTP Server
Runs on Termux, exposes endpoints for remote control.
Endpoints: /exec, /toast, /speak, /vibrate, /write_file, /listen, /health
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
from http.server import HTTPServer, BaseHTTPRequestHandler

AUTH_TOKEN = "amos-bridge-2026"
PORT = 8080
LOG_FILE = os.path.expanduser("~/bridge.log")

# --- Logging setup (file + stderr, unbuffered) ---
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
    """Kill any process holding the port. Works without root on Termux."""
    try:
        r = subprocess.run(
            f"lsof -ti:{port}", shell=True, capture_output=True, text=True
        )
        pids = r.stdout.strip().split()
        for pid in pids:
            if pid:
                os.kill(int(pid), signal.SIGTERM)
                log.info("Killed stale process %s on port %d", pid, port)
    except Exception:
        pass  # lsof may not exist; we handle bind failure below


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
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def _read_body(self):
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return {}
        return json.loads(self.rfile.read(length))

    def do_GET(self):
        if self.path == "/health":
            self._respond(200, {"status": "ok", "version": "2.4"})
            return
        self._respond(404, {"error": "not found"})

    def do_POST(self):
        if not self._auth():
            return
        try:
            body = self._read_body()
        except Exception as e:
            self._respond(400, {"error": f"bad request: {e}"})
            return

        routes = {
            "/exec": self._handle_exec,
            "/toast": self._handle_toast,
            "/speak": self._handle_speak,
            "/vibrate": self._handle_vibrate,
            "/write_file": self._handle_write_file,
            "/listen": self._handle_listen,
        }
        handler = routes.get(self.path)
        if handler:
            handler(body)
        else:
            self._respond(404, {"error": "not found"})

    def _run(self, cmd, timeout=30):
        try:
            r = subprocess.run(
                cmd, shell=True, capture_output=True, text=True, timeout=timeout
            )
            return r.returncode, r.stdout.strip(), r.stderr.strip()
        except subprocess.TimeoutExpired:
            return -1, "", "timeout"
        except Exception as e:
            return -1, "", str(e)

    def _handle_exec(self, body):
        cmd = body.get("cmd", "")
        if not cmd:
            self._respond(400, {"error": "missing cmd"})
            return
        # Async mode: fire-and-forget for long-running commands
        if body.get("async", False):
            subprocess.Popen(
                cmd, shell=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            log.info("Exec (async): %s", cmd[:80])
            self._respond(200, {"status": "started", "async": True, "cmd": cmd})
            return
        timeout = body.get("timeout", 30)
        code, stdout, stderr = self._run(cmd, timeout=timeout)
        self._respond(200, {"returncode": code, "stdout": stdout, "stderr": stderr})

    def _handle_toast(self, body):
        text = body.get("text", "AMOS")
        code, stdout, stderr = self._run(f'termux-toast "{text}"')
        self._respond(200, {"ok": code == 0, "stderr": stderr})

    def _handle_speak(self, body):
        text = body.get("text", "")
        if not text:
            self._respond(400, {"error": "missing text"})
            return
        # Fire-and-forget: don't wait for TTS to finish (avoids tunnel timeout)
        safe_text = text.replace('"', '\\"')
        subprocess.Popen(
            f'termux-tts-speak "{safe_text}"',
            shell=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        log.info("Speaking (async): %s", text[:80])
        self._respond(200, {"status": "speaking", "text": text})

    def _handle_vibrate(self, body):
        ms = body.get("ms", 500)
        code, stdout, stderr = self._run(f"termux-vibrate -d {ms}")
        self._respond(200, {"ok": code == 0, "stderr": stderr})

    def _handle_write_file(self, body):
        path = body.get("path", "")
        content = body.get("content", "")
        b64 = body.get("base64", False)
        if not path:
            self._respond(400, {"error": "missing path"})
            return
        try:
            os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
            if b64:
                data = base64.b64decode(content)
                with open(path, "wb") as f:
                    f.write(data)
            else:
                with open(path, "w") as f:
                    f.write(content)
            self._respond(200, {"ok": True, "path": path})
        except Exception as e:
            self._respond(500, {"error": str(e)})


    def _handle_listen(self, body):
        """Record audio via mic and transcribe via OpenAI Whisper API.
        
        Pipeline: termux-microphone-record -> Whisper API -> text
        
        Params:
            seconds: recording duration (default 5, max 30)
            openai_key: OpenAI API key (or set OPENAI_API_KEY env var)
        Returns:
            {"text": "transcribed speech", "status": "ok"} or
            {"text": "", "status": "no_speech"} or
            {"text": "", "status": "error", "error": "..."}
        """
        seconds = min(body.get("seconds", 5), 30)
        openai_key = body.get("openai_key", "") or os.environ.get("OPENAI_API_KEY", "")
        
        audio_file = os.path.expanduser("~/ears_recording.wav")
        
        # Kill any lingering TTS to release audio hardware
        subprocess.run(['pkill', '-f', 'termux-tts-speak'], capture_output=True, timeout=3)
        time.sleep(2)  # Wait for audio hardware release
        
        # Step 1: Clean up previous recording
        self._run(f"rm -f {audio_file}")
        # Kill any lingering recorder process
        self._run("termux-microphone-record -q 2>/dev/null || true", timeout=3)
        time.sleep(0.3)
        
        # Step 2: Record audio via termux-microphone-record
        log.info("Recording %ds of audio...", seconds)
        rec_code, _, rec_err = self._run(
            f"termux-microphone-record -f {audio_file} -l {seconds} -e amr_wb",
            timeout=5
        )
        
        if rec_code != 0:
            log.warning("Mic record start failed: %s", rec_err)
            self._respond(200, {"text": "", "status": "error", "error": f"mic_start_failed: {rec_err}"})
            return
        
        # Step 3: Wait for recording to complete
        time.sleep(seconds + 1)
        
        # Step 4: Stop recording explicitly
        self._run("termux-microphone-record -q 2>/dev/null || true", timeout=3)
        time.sleep(0.3)
        
        # Step 5: Check audio file exists and has content
        stat_code, stat_out, _ = self._run(f"stat -c %s {audio_file} 2>/dev/null || echo 0")
        file_size = int(stat_out) if stat_out.isdigit() else 0
        
        if file_size < 100:
            log.warning("Audio file too small or missing: %d bytes", file_size)
            self._respond(200, {"text": "", "status": "no_speech", "error": "audio_empty", "file_size": file_size})
            return
        
        log.info("Audio captured: %d bytes", file_size)
        
        # Step 6: If no API key, return base64 audio (fallback mode)
        if not openai_key:
            log.info("No OpenAI key - returning base64 audio")
            b64_code, b64_out, b64_err = self._run(f"base64 -w 0 {audio_file}", timeout=10)
            if b64_code == 0 and b64_out:
                self._respond(200, {
                    "text": "",
                    "status": "no_key",
                    "audio_b64": b64_out,
                    "file_size": file_size,
                    "format": "amr_wb",
                    "error": "No OpenAI API key. Pass openai_key in body or set OPENAI_API_KEY env var."
                })
            else:
                self._respond(200, {"text": "", "status": "error", "error": f"base64_failed: {b64_err}"})
            return
        
        # Step 7: Send to OpenAI Whisper API via curl
        log.info("Transcribing via Whisper API...")
        whisper_cmd = (
            f'curl -s -X POST https://api.openai.com/v1/audio/transcriptions '
            f'-H "Authorization: Bearer {openai_key}" '
            f'-F "model=whisper-1" '
            f'-F "file=@{audio_file}" '
            f'-F "response_format=json"'
        )
        
        w_code, w_out, w_err = self._run(whisper_cmd, timeout=30)
        
        if w_code != 0:
            log.warning("Whisper API call failed: %s", w_err)
            self._respond(200, {"text": "", "status": "error", "error": f"whisper_failed: {w_err}"})
            return
        
        # Step 8: Parse Whisper response
        try:
            whisper_resp = json.loads(w_out)
            text = whisper_resp.get("text", "").strip()
            
            if text:
                log.info("Heard: %s", text[:100])
                self._respond(200, {"text": text, "status": "ok"})
            else:
                log.info("Whisper returned empty text")
                self._respond(200, {"text": "", "status": "no_speech"})
        except json.JSONDecodeError:
            log.warning("Whisper response not JSON: %s", w_out[:200])
            self._respond(200, {"text": "", "status": "error", "error": f"whisper_parse_error: {w_out[:200]}"})

    def log_message(self, fmt, *args):
        log.info("%s %s", self.client_address[0], fmt % args)


if __name__ == "__main__":
    try:
        # Kill anything squatting on our port
        kill_port(PORT)

        # SO_REUSEADDR: let the OS rebind immediately
        class ReusableHTTPServer(HTTPServer):
            allow_reuse_address = True
            # Also allow reuse on Linux/Termux
            def server_bind(self):
                self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                super().server_bind()

        server = ReusableHTTPServer(("0.0.0.0", PORT), BridgeHandler)
        log.info("AMOS Bridge v2.1 listening on 0.0.0.0:%d", PORT)
        print(f"AMOS Bridge v2.1 listening on 0.0.0.0:{PORT}", flush=True)
        server.serve_forever()

    except OSError as e:
        log.error("FATAL: Cannot bind port %d -- %s", PORT, e)
        print(f"FATAL: Cannot bind port {PORT} -- {e}", file=sys.stderr, flush=True)
        sys.exit(1)

    except KeyboardInterrupt:
        log.info("Bridge shutting down.")
        print("Bridge shutting down.", flush=True)
        server.server_close()

    except Exception as e:
        log.error("FATAL: Unexpected error -- %s", e, exc_info=True)
        print(f"FATAL: {e}", file=sys.stderr, flush=True)
        sys.exit(1)
