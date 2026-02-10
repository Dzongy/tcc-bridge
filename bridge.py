#!/usr/bin/env python3
"""AMOS Bridge v4.0 - Phone Control HTTP Server
Runs on Termux, exposes endpoints for remote control.
Endpoints: /exec, /toast, /speak, /vibrate, /write_file, /listen, /conversation, /health, /voice
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
    """Kill any process holding the port. Skips own PID. Works without root on Termux."""
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
            self._respond(200, {"status": "ok", "version": "4.0"})
            return
        if self.path == "/voice":
            self._serve_voice_html()
            return
        self._respond(404, {"error": "not found"})

    def _serve_voice_html(self):
        try:
            html_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "voice.html")
            with open(html_path, "r", encoding="utf-8") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(content.encode("utf-8"))))
            self.end_headers()
            self.wfile.write(content.encode("utf-8"))
        except FileNotFoundError:
            self._respond(404, {"error": "voice.html not found"})
        except Exception as e:
            self._respond(500, {"error": f"failed to serve voice.html: {e}"})

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
            "/conversation": self._handle_conversation,
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
        # Blocking TTS: wait for speech to finish before returning (prevents overlap with beep/recording)
        safe_text = text.replace('"', '\\"')
        try:
            subprocess.run(
                f'termux-tts-speak "{safe_text}"',
                shell=True,
                capture_output=True,
                timeout=30,
            )
        except subprocess.TimeoutExpired:
            log.warning("TTS timed out after 30s: %s", text[:80])
        log.info("Speaking (blocking): %s", text[:80])
        self._respond(200, {"status": "spoken", "text": text})

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
        
        audio_file = os.path.expanduser("~/ears_recording.m4a")
        
        # Kill any lingering TTS to release audio hardware
        subprocess.run(['pkill', '-f', 'termux-tts-speak'], capture_output=True, timeout=3)
        time.sleep(2)  # Wait for audio hardware release
        
        # Step 1: Clean up previous recording
        self._run(f"rm -f {audio_file}")
        # Kill any lingering recorder process
        self._run("termux-microphone-record -q 2>/dev/null || true", timeout=3)
        time.sleep(0.3)
        
        # Beep before recording
        self._run('termux-tts-speak "beep"', timeout=5)
        
        # Step 2: Record audio via termux-microphone-record
        log.info("Recording %ds of audio...", seconds)
        rec_code, _, rec_err = self._run(
            f"termux-microphone-record -f {audio_file} -l {seconds} -e aac",
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
                    "format": "aac",
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

    def _speak_sync(self, text):
        """Speak text and wait for TTS to finish before returning."""
        safe_text = text.replace('"', '\\"')
        code, _, err = self._run(f'termux-tts-speak "{safe_text}"', timeout=60)
        if code != 0:
            log.warning("TTS failed: %s", err)
        time.sleep(0.5)  # Small buffer after speech

    def _handle_conversation(self, body):
        """Always-on voice conversation loop with OpenAI GPT-4o.
        
        Params:
            openai_key: OpenAI API key (required)
            system_prompt: system prompt for GPT (default: Cosmic Claw persona)
        Returns:
            {"status": "ok", "transcript": [...], "rounds_completed": N}
        Exit phrases: stop, goodbye, peace out, shut down, exit, quit
        """
        openai_key = body.get("openai_key", "") or os.environ.get("OPENAI_API_KEY", "")
        if not openai_key:
            self._respond(400, {"error": "missing openai_key"})
            return
        
        EXIT_PHRASES = ["stop", "goodbye", "peace out", "shut down", "exit", "quit"]
        system_prompt = body.get("system_prompt", 
            "You are The Cosmic Claw, an AI hive mind. Be witty, direct, magnetic. Grok style. Keep responses under 3 sentences.")
        
        # Conversation history for context
        messages = [{"role": "system", "content": system_prompt}]
        transcript = []
        
        # First round: introduce
        intro = "The Cosmic Claw is online. Talk to me."
        self._speak_sync(intro)
        transcript.append({"role": "assistant", "content": intro})
        messages.append({"role": "assistant", "content": intro})
        
        log.info("Conversation started: always-on mode (exit phrases active)")
        
        round_num = 0
        while True:
            round_num += 1
            log.info("=== Conversation round %d ===", round_num)
            
            # Beep then listen (non-blocking via play-audio)
            self._run('termux-tts-speak "beep"', timeout=5)
            
            # Record 10 seconds
            audio_file = os.path.expanduser("~/ears_recording.m4a")
            self._run(f"rm -f {audio_file}")
            self._run("termux-microphone-record -q 2>/dev/null || true", timeout=3)
            time.sleep(0.3)
            
            rec_code, _, rec_err = self._run(
                f"termux-microphone-record -f {audio_file} -l 10 -e aac",
                timeout=5
            )
            if rec_code != 0:
                log.warning("Mic failed in conversation round %d: %s", i + 1, rec_err)
                self._speak_sync("Microphone error. Ending conversation.")
                transcript.append({"role": "system", "content": f"mic_error: {rec_err}"})
                break
            
            time.sleep(11)  # Wait for recording
            self._run("termux-microphone-record -q 2>/dev/null || true", timeout=3)
            time.sleep(0.3)
            
            # Check file
            stat_code, stat_out, _ = self._run(f"stat -c %s {audio_file} 2>/dev/null || echo 0")
            file_size = int(stat_out) if stat_out.isdigit() else 0
            
            if file_size < 100:
                log.info("Empty audio in round %d, retrying", i + 1)
                self._speak_sync("I didn't catch that. Try again.")
                transcript.append({"role": "system", "content": "no_speech_retry"})
                continue
            
            # Transcribe
            whisper_cmd = (
                f'curl -s -X POST https://api.openai.com/v1/audio/transcriptions '
                f'-H "Authorization: Bearer {openai_key}" '
                f'-F "model=whisper-1" '
                f'-F "file=@{audio_file}" '
                f'-F "response_format=json"'
            )
            w_code, w_out, w_err = self._run(whisper_cmd, timeout=30)
            
            if w_code != 0:
                log.warning("Whisper failed in round %d: %s", i + 1, w_err)
                self._speak_sync("I didn't catch that. Try again.")
                transcript.append({"role": "system", "content": f"whisper_error: {w_err}"})
                continue
            
            try:
                whisper_resp = json.loads(w_out)
                user_text = whisper_resp.get("text", "").strip()
            except json.JSONDecodeError:
                log.warning("Whisper parse error round %d: %s", i + 1, w_out[:200])
                self._speak_sync("I didn't catch that. Try again.")
                transcript.append({"role": "system", "content": "whisper_parse_error"})
                continue
            
            if not user_text:
                log.info("No speech detected round %d", i + 1)
                self._speak_sync("I didn't catch that. Try again.")
                transcript.append({"role": "system", "content": "no_speech"})
                continue
            
            log.info("User said: %s", user_text[:100])
            transcript.append({"role": "user", "content": user_text})
            messages.append({"role": "user", "content": user_text})
            
            # Call GPT-4o
            chat_payload = json.dumps({
                "model": "gpt-4o",
                "messages": messages,
                "max_tokens": 200,
                "temperature": 0.9
            })
            
            # Write payload to temp file to avoid shell escaping issues
            payload_file = os.path.expanduser("~/chat_payload.json")
            with open(payload_file, "w") as f:
                f.write(chat_payload)
            
            chat_cmd = (
                f'curl -s -X POST https://api.openai.com/v1/chat/completions '
                f'-H "Authorization: Bearer {openai_key}" '
                f'-H "Content-Type: application/json" '
                f'-d @{payload_file}'
            )
            c_code, c_out, c_err = self._run(chat_cmd, timeout=45)
            
            if c_code != 0:
                log.warning("GPT call failed round %d: %s", i + 1, c_err)
                transcript.append({"role": "system", "content": f"gpt_error: {c_err}"})
                break
            
            try:
                chat_resp = json.loads(c_out)
                if "error" in chat_resp:
                    log.warning("GPT API error round %d: %s", i + 1, chat_resp["error"])
                    transcript.append({"role": "system", "content": f"gpt_api_error: {chat_resp['error']}"})
                    break
                ai_text = chat_resp["choices"][0]["message"]["content"].strip()
            except (json.JSONDecodeError, KeyError, IndexError) as e:
                log.warning("GPT parse error round %d: %s", i + 1, str(e))
                transcript.append({"role": "system", "content": f"gpt_parse_error: {c_out[:200]}"})
                break
            
            log.info("AI says: %s", ai_text[:100])
            transcript.append({"role": "assistant", "content": ai_text})
            messages.append({"role": "assistant", "content": ai_text})
            
            # Speak the response
            self._speak_sync(ai_text)
        
        log.info("Conversation complete: %d entries in transcript", len(transcript))
        self._respond(200, {
            "status": "ok",
            "transcript": transcript,
            "rounds_completed": len([t for t in transcript if t["role"] == "user"])
        })

    def log_message(self, fmt, *args):
        log.info("%s %s", self.client_address[0], fmt % args)


def _sigterm_handler(signum, frame):
    log.info("Received SIGTERM, shutting down gracefully.")
    sys.exit(0)

signal.signal(signal.SIGTERM, _sigterm_handler)


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
        log.info("AMOS Bridge v3.3 listening on 0.0.0.0:%d", PORT)
        print(f"AMOS Bridge v3.3 listening on 0.0.0.0:{PORT}", flush=True)
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