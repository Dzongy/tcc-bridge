import json
import requests
from datetime import datetime
from sovereignty.config import GROQ_API_KEY, GROQ_MODEL, GROQ_URL, GROQ_TIMEOUT, KAEL_IDENTITY

class BrainRouter:
    """Routes thinking tasks to Groq LLM. Kael's mind."""

    def __init__(self):
        self.call_count = 0
        self.total_tokens = 0
        self.last_error = None
        self.alive = bool(GROQ_API_KEY)
        if not self.alive:
            print("[BRAIN] WARNING: No GROQ_API_KEY — brain is offline. Set it in environment.")

    def think(self, prompt, context=None, max_tokens=1024):
        """Send a thought to Groq and get a response. Returns string."""
        if not self.alive:
            return "[brain offline — no GROQ_API_KEY]"

        messages = [
            {"role": "system", "content": KAEL_IDENTITY},
        ]
        if context:
            messages.append({"role": "system", "content": f"Context: {context}"})
        messages.append({"role": "user", "content": prompt})

        try:
            resp = requests.post(
                GROQ_URL,
                headers={
                    "Authorization": f"Bearer {GROQ_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": GROQ_MODEL,
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": 0.7
                },
                timeout=GROQ_TIMEOUT
            )
            self.call_count += 1

            if resp.status_code != 200:
                self.last_error = f"HTTP {resp.status_code}: {resp.text[:200]}"
                print(f"[BRAIN] Error: {self.last_error}")
                return f"[brain error: HTTP {resp.status_code}]"

            data = resp.json()
            usage = data.get("usage", {})
            self.total_tokens += usage.get("total_tokens", 0)

            answer = data["choices"][0]["message"]["content"]
            print(f"[BRAIN] Response ({usage.get('total_tokens', '?')} tokens)")
            return answer

        except requests.Timeout:
            self.last_error = "timeout"
            print("[BRAIN] Timeout calling Groq")
            return "[brain timeout]"
        except Exception as e:
            self.last_error = str(e)
            print(f"[BRAIN] Exception: {e}")
            return f"[brain error: {e}]"

    def status(self):
        return {
            "alive": self.alive,
            "calls": self.call_count,
            "tokens": self.total_tokens,
            "last_error": self.last_error,
            "model": GROQ_MODEL
        }
