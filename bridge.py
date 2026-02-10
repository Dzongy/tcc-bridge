#!/usr/bin/env python3
"""AMOS Bridge v3.1 â Bulletproof mic + watchdog auto-restart"""
import os, sys, json, time, subprocess, tempfile, base64, threading, signal
from http.server import HTTPServer, BaseHTTPRequestHandler

# ââ Config ââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
PORT = int(os.environ.get("BRIDGE_PORT", 8080))
AUTH_TOKEN = os.environ.get("BRIDGE_AUTH", "amos-bridge-2026")
OPENAI_API_URL = "https://api.openai.com/v1"
RECORD_SECONDS = 8
MAX_MIC_RETRIES = 3

# ââ Helpers âââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ

def tts_speak(text):
    """Speak text via termux-tts-speak and wait for completion."""
    try:
        subprocess.run(["termux-tts-speak", "-r", "1.0", text],
                       timeout=60, check=False)
        # Give TTS engine time to fully release audio device
        time.sleep(1)
    except Exception as e:
        print(f"[TTS] Error: {e}")


def record_audio(path, seconds=RECORD_SECONDS):
    """Record audio via termux-microphone-record. Returns True on success."""
    # Kill any lingering recording processes first
    subprocess.run(["pkill", "-f", "termux-microphone-record"],
                   capture_output=True, timeout=5)
    time.sleep(0.5)

    try:
        # Start recording
        subprocess.run(
            ["termux-microphone-record", "-f", path, "-l", str(seconds)],
            timeout=seconds + 10, check=True
        )
        time.sleep(0.5)
        # Verify file exists and has content
        if os.path.exists(path) and os.path.getsize(path) > 1000:
            return True
        print(f"[MIC] Recording file too small or missing: {path}")
        return False
    except subprocess.TimeoutExpired:
        print("[MIC] Recording timed out")
        subprocess.run(["pkill", "-f", "termux-microphone-record"],
                       capture_output=True, timeout=5)
        return False
    except Exception as e:
        print(f"[MIC] Recording error: {e}")
        return False


def whisper_transcribe(audio_path, openai_key):
    """Transcribe audio file using OpenAI Whisper API."""
    import urllib.request, urllib.error
    url = f"{OPENAI_API_URL}/audio/transcriptions"

    with open(audio_path, "rb") as f:
        audio_data = f.read()

    boundary = "----AMOSBoundary"
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="audio.m4a"\r\n'
        f"Content-Type: audio/m4a\r\n\r\n"
    ).encode() + audio_data + (
        f"\r\n--{boundary}\r\n"
        f'Content-Disposition: form-data; name="model"\r\n\r\n'
        f"whisper-1\r\n"
        f"--{boundary}--\r\n"
    ).encode()

    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Authorization", f"Bearer {openai_key}")
    req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode())
            return result.get("text", "").strip()
    except Exception as e:
        print(f"[WHISPER] Error: {e}")
        return ""


def gpt_respond(messages, openai_key, system_prompt):
    """Get GPT-4o response."""
    import urllib.request
    url = f"{OPENAI_API_URL}/chat/completions"

    full_messages = [{"role": "system", "content": system_prompt}] + messages

    payload = json.dumps({
        "model": "gpt-4o",
        "messages": full_messages,
        "max_tokens": 300,
        "temperature": 0.8
    }).encode()

    req = urllib.request.Request(url, data=payload, method="POST")
    req.add_header("Authorization", f"Bearer {openai_key}")
    req.add_header("Content-Type", "application/json")

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode())
            return result["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"[GPT] Error: {e}")
        return "I had trouble thinking of a response. Could you say that again?"


# ââ Request Handler âââââââââââââââââââââââââââââââââââââââââââââââââââââ

class BridgeHandler(BaseHTTPRequestHandler):

    def _send_json(self, code, data):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def _auth_ok(self):
        token = self.headers.get("X-Auth", "")
        if token != AUTH_TOKEN:
            self._send_json(401, {"error": "unauthorized"})
            return False
        return True

    def _read_body(self):
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return {}
        return json.loads(self.rfile.read(length).decode())

    def do_GET(self):
        if self.path == "/health":
            self._send_json(200, {
                "status": "alive",
                "version": "3.1",
                "features": ["bulletproof_mic", "watchdog"]
            })
            return
        self._send_json(404, {"error": "not found"})

    def do_POST(self):
        if not self._auth_ok():
            return

        if self.path == "/exec":
            self._handle_exec()
        elif self.path == "/tts":
            self._handle_tts()
        elif self.path == "/conversation":
            self._handle_conversation()
        else:
            self._send_json(404, {"error": "not found"})

    def _handle_exec(self):
        body = self._read_body()
        cmd = body.get("cmd", "")
        timeout = body.get("timeout", 30)
        try:
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True,
                timeout=timeout
            )
            self._send_json(200, {
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode
            })
        except subprocess.TimeoutExpired:
            self._send_json(200, {
                "stdout": "",
                "stderr": "Command timed out",
                "returncode": -1
            })
        except Exception as e:
            self._send_json(500, {"error": str(e)})

    def _handle_tts(self):
        body = self._read_body()
        text = body.get("text", "")
        if not text:
            self._send_json(400, {"error": "no text"})
            return
        tts_speak(text)
        self._send_json(200, {"status": "spoken", "text": text})

    def _handle_conversation(self):
        body = self._read_body()
        openai_key = body.get("openai_key", "")
        system_prompt = body.get("system_prompt",
            "You are AMOS, a friendly AI assistant living on a phone. "
            "Keep responses concise and conversational (2-3 sentences max). "
            "Be warm, helpful, and natural.")
        rounds = body.get("rounds", 5)
        # rounds=0 means unlimited â conversation ends when user says exit phrase
        max_rounds = rounds if rounds > 0 else 999

        if not openai_key:
            self._send_json(400, {"error": "openai_key required"})
            return

        transcript = []
        messages = []

        # Greeting
        greeting = "Hey! I'm AMOS. What's on your mind?"
        tts_speak(greeting)
        transcript.append({"role": "assistant", "text": greeting})

        round_num = 0
        while round_num < max_rounds:
            # ââ 2-second cooldown between rounds for mic hardware reset ââ
            time.sleep(2)

            # ââ Recording with retry logic ââ
            user_text = ""
            mic_success = False

            for attempt in range(MAX_MIC_RETRIES):
                try:
                    # Kill lingering mic processes before each attempt
                    subprocess.run(["pkill", "-f", "termux-microphone-record"],
                                   capture_output=True, timeout=5)
                    time.sleep(0.5)

                    with tempfile.NamedTemporaryFile(suffix=".m4a", delete=False) as tmp:
                        audio_path = tmp.name

                    print(f"[MIC] Round {round_num+1}, attempt {attempt+1}/{MAX_MIC_RETRIES}")

                    if record_audio(audio_path):
                        user_text = whisper_transcribe(audio_path, openai_key)

                        if user_text:
                            mic_success = True
                            break
                        else:
                            print(f"[WHISPER] No speech detected, retrying...")
                            # Don't count no-speech as attempt failure, but do retry
                    else:
                        print(f"[MIC] Recording failed, attempt {attempt+1}")

                except Exception as e:
                    print(f"[MIC] Exception on attempt {attempt+1}: {e}")

                finally:
                    # Clean up temp file
                    try:
                        if 'audio_path' in dir() and os.path.exists(audio_path):
                            os.unlink(audio_path)
                    except:
                        pass

                # Brief pause before retry
                time.sleep(1)

            if not mic_success:
                # All retries exhausted for this round â skip and try next round
                print(f"[MIC] All {MAX_MIC_RETRIES} attempts failed for round {round_num+1}, skipping")
                tts_speak("I couldn't hear you. Let's try again.")
                transcript.append({
                    "role": "system",
                    "text": f"Mic failed after {MAX_MIC_RETRIES} retries on round {round_num+1}"
                })
                round_num += 1
                continue

            print(f"[USER] {user_text}")
            transcript.append({"role": "user", "text": user_text})
            messages.append({"role": "user", "content": user_text})

            # Check for exit phrases
            lower = user_text.lower()
            exit_phrases = ["peace out", "goodbye", "exit", "quit", "stop",
                          "end conversation", "that's all", "bye"]
            if any(phrase in lower for phrase in exit_phrases):
                farewell = "Peace! Catch you later."
                tts_speak(farewell)
                transcript.append({"role": "assistant", "text": farewell})
                break

            # Get GPT response
            reply = gpt_respond(messages, openai_key, system_prompt)
            print(f"[AMOS] {reply}")
            messages.append({"role": "assistant", "content": reply})
            transcript.append({"role": "assistant", "text": reply})
            tts_speak(reply)

            round_num += 1

        self._send_json(200, {
            "status": "completed",
            "rounds_completed": round_num,
            "transcript": transcript
        })


# ââ Main ââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ

def main():
    server = HTTPServer(("0.0.0.0", PORT), BridgeHandler)
    print(f"[BRIDGE] AMOS Bridge v3.1 listening on port {PORT}")
    print(f"[BRIDGE] Features: bulletproof mic, watchdog support")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[BRIDGE] Shutting down...")
        server.server_close()

if __name__ == "__main__":
    main()
