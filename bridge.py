#!/usr/bin/env python3
"""AMOS Bridge v2.3 - Phone Control HTTP Server
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
            self._respond(200, {"status": "ok", "version": "2.3"})
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
        """Record audio and transcribe via on-device STT.
        
        Params:
            seconds: recording duration (default 5, max 30)
            mode: "stt" (default) uses termux-speech-to-text,
                  "record" returns base64 audio for external STT
        """
        seconds = min(body.get("seconds", 5), 30)
        mode = body.get("mode", "stt")
        
        if mode == "stt":
            # Use termux-speech-to-text (Google on-device, blocks until speech ends)
            log.info("Listening for speech (timeout %ds)...", seconds)
            code, stdout, stderr = self._run(
                f"timeout {seconds + 5} termux-speech-to-text",
                timeout=seconds + 10
            )
            if code == 0 and stdout:
                log.info("Heard: %s", stdout[:100])
                self._respond(200, {"text": stdout, "mode": "stt"})
            else:
                self._respond(200, {
                    "text": "",
                    "error": stderr or "no speech detected",
                    "mode": "stt",
                    "returncode": code
                })
        
        elif mode == "record":
            # Record audio, base64 encode, return for external STT
            audio_file = os.path.expanduser("~/ears_recording.wav")
            
            # Clean up any previous recording
            self._run(f"rm -f {audio_file}")
            
            # Record audio
            log.info("Recording %ds of audio...", seconds)
            rec_code, _, rec_err = self._run(
                f"termux-microphone-record -f {audio_file} -l {seconds} -e amr_wb",
                timeout=seconds + 5
            )
            
            # Wait for recording to finish
            time.sleep(seconds + 1)
            
            # Stop recording explicitly
            self._run("termux-microphone-record -q", timeout=5)
            
            # Check file exists and encode
            if os.path.exists(audio_file):
                with open(audio_file, "rb") as f:
                    audio_b64 = base64.b64encode(f.read()).decode()
                file_size = os.path.getsize(audio_file)
                log.info("Recorded %d bytes of audio", file_size)
                self._respond(200, {
                    "audio_base64": audio_b64,
                    "file_size": file_size,
                    "format": "amr_wb",
                    "seconds": seconds,
                    "mode": "record"
                })
            else:
                self._respond(500, {
                    "error": "recording failed",
                    "stderr": rec_err,
                    "mode": "record"
                })
        
        else:
            self._respond(400, {"error": f"unknown mode: {mode}, use 'stt' or 'record'"})

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
