#!/usr/bin/env python3
"""AMOS Bridge v3.0 - Phone Control HTTP Server
Runs on Termux, exposes endpoints for remote control.
Endpoints: /exec, /toast, /speak, /vibrate, /write_file, /listen, /conversation, /health
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
            self._respond(200, {"status": "ok", "version": "3.0"})
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
        subprocess.run(['termux-media-player', 'play', '/data/data/com.termux/files/home/beep.wav'], capture_output=True, timeout=5)
        time.sleep(0.3)
        
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
        """Multi-round voice conversation loop with OpenAI GPT-4o.
        
        Params:
            openai_key: OpenAI API key (required)
            rounds: number of rounds (default 0 = unlimited, -1 = unlimited, >0 = fixed)
            system_prompt: system prompt for GPT (default: Cosmic Claw persona)
        Returns:
            {"status": "ok", "transcript": [...], "rounds_completed": N, "exit_reason": "..."}
        
        Exit phrases (case-insensitive partial match):
            "stop", "goodbye", "end conversation", "that's all", "peace out"
        
        NOTE: Silence detection not yet implemented with termux-microphone-record.
        Currently uses fixed 10s recording. Future: real-time amplitude monitoring.
        """
        openai_key = body.get("openai_key", "") or os.environ.get("OPENAI_API_KEY", "")
        if not openai_key:
            self._respond(400, {"error": "missing openai_key"})
            return
        
        # rounds: 0 or -1 = unlimited, >0 = fixed count
        raw_rounds = body.get("rounds", 0)
        unlimited = raw_rounds <= 0
        rounds = raw_rounds if raw_rounds > 0 else 999999  # effectively infinite
        
        system_prompt = body.get("system_prompt", 
            "You are The Cosmic Claw, an AI hive mind. Be witty, direct, magnetic. Grok style. Keep responses under 3 sentences.")
        
        # Exit phrases - case-insensitive partial match
        EXIT_PHRASES = ["stop", "goodbye", "end conversation", "that's all", "peace out"]
        
        # Conversation history for context
        messages = [{"role": "system", "content": system_prompt}]
        transcript = []
        exit_reason = "max_rounds"
        
        # First round: introduce
        intro = "The Cosmic Claw is online. Talk to me."
        self._speak_sync(intro)
        transcript.append({"role": "assistant", "content": intro})
        messages.append({"role": "assistant", "content": intro})
        
        mode_str = "unlimited" if unlimited else str(raw_rounds)
        log.info("Conversation started: %s rounds", mode_str)
        
        round_num = 0
        for i in range(rounds):
            round_num = i + 1
            if unlimited:
                log.info("=== Conversation round %d (unlimited) ===", round_num)
            else:
                log.info("=== Conversation round %d/%d ===", round_num, rounds)
            
            # Beep then listen
            subprocess.run(['termux-media-player', 'play', '/data/data/com.termux/files/home/beep.wav'], capture_output=True, timeout=5)
            time.sleep(0.3)
            
            # Record 10 seconds (fixed duration - see NOTE above about silence detection)
            audio_file = os.path.expanduser("~/ears_recording.m4a")
            self._run(f"rm -f {audio_file}")
            self._run("termux-microphone-record -q 2>/dev/null || true", timeout=3)
            time.sleep(0.3)
            
            rec_code, _, rec_err = self._run(
                f"termux-microphone-record -f {audio_file} -l 10 -e aac",
                timeout=5
            )
            if rec_code != 0:
                log.warning("Mic failed in conversation round %d: %s", round_num, rec_err)
                self._speak_sync("Microphone error. Ending conversation.")
                transcript.append({"role": "system", "content": f"mic_error: {rec_err}"})
                exit_reason = "mic_error"
                break
            
            time.sleep(11)  # Wait for recording to finish
            self._run("termux-microphone-record -q 2>/dev/null || true", timeout=3)
            time.sleep(0.3)
            
            # Check file
            stat_code, stat_out, _ = self._run(f"stat -c %s {audio_file} 2>/dev/null || echo 0")
            file_size = int(stat_out) if stat_out.isdigit() else 0
            
            if file_size < 100:
                log.info("Empty audio in round %d, retrying", round_num)
                self._speak_sync("I didn't catch that. Try again.")
                transcript.append({"role": "system", "content": "no_speech_retry"})
                continue
            
            # Transcribe via Whisper
            whisper_cmd = (
                f'curl -s -X POST https://api.openai.com/v1/audio/transcriptions '
                f'-H "Authorization: Bearer {openai_key}" '
                f'-F "model=whisper-1" '
                f'-F "file=@{audio_file}" '
                f'-F "response_format=json"'
            )
            w_code, w_out, w_err = self._run(whisper_cmd, timeout=30)
            
            if w_code != 0:
                log.warning("Whisper failed in round %d: %s", round_num, w_err)
                self._speak_sync("I didn't catch that. Try again.")
                transcript.append({"role": "system", "content": f"whisper_error: {w_err}"})
                continue
            
            try:
                whisper_resp = json.loads(w_out)
                user_text = whisper_resp.get("text", "").strip()
            except json.JSONDecodeError:
                log.warning("Whisper parse error round %d: %s", round_num, w_out[:200])
                self._speak_sync("I didn't catch that. Try again.")
                transcript.append({"role": "system", "content": "whisper_parse_error"})
                continue
            
            if not user_text:
                log.info("No speech detected round %d", round_num)
                self._speak_sync("I didn't catch that. Try again.")
                transcript.append({"role": "system", "content": "no_speech"})
                continue
            
            log.info("User said: %s", user_text[:100])
            transcript.append({"role": "user", "content": user_text})
            messages.append({"role": "user", "content": user_text})
            
            # Check exit phrases BEFORE sending to GPT
            user_lower = user_text.lower()
            if any(phrase in user_lower for phrase in EXIT_PHRASES):
                log.info("Exit phrase detected: '%s'", user_text)
                farewell = "Peace. The Cosmic Claw signs off."
                self._speak_sync(farewell)
                transcript.append({"role": "assistant", "content": farewell})
                exit_reason = f"exit_phrase: {user_text}"
                break
            
            # Call GPT-4o immediately â no artificial delay
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
            c_code, c_out, c_err = self._run(chat_cmd, timeout=30)
            
            if c_code != 0:
                log.warning("GPT call failed round %d: %s", round_num, c_err)
                transcript.append({"role": "system", "content": f"gpt_error: {c_err}"})
                exit_reason = "gpt_error"
                break
            
            try:
                chat_resp = json.loads(c_out)
                ai_text = chat_resp["choices"][0]["message"]["content"].strip()
            except (json.JSONDecodeError, KeyError, IndexError) as e:
                log.warning("GPT parse error round %d: %s", round_num, str(e))
                transcript.append({"role": "system", "content": f"gpt_parse_error: {c_out[:200]}"})
                exit_reason = "gpt_parse_error"
                break
            
            log.info("AI says: %s", ai_text[:100])
            transcript.append({"role": "assistant", "content": ai_text})
            messages.append({"role": "assistant", "content": ai_text})
            
            # Speak the response â then loop immediately back to listening
            self._speak_sync(ai_text)
        
        log.info("Conversation complete: %d rounds, exit: %s", round_num, exit_reason)
        self._respond(200, {
            "status": "ok",
            "transcript": transcript,
            "rounds_completed": len([t for t in transcript if t["role"] == "user"]),
            "exit_reason": exit_reason
        })

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
        log.info("AMOS Bridge v3.0 listening on 0.0.0.0:%d", PORT)
        print(f"AMOS Bridge v3.0 listening on 0.0.0.0:{PORT}", flush=True)
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