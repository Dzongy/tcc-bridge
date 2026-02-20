import signal
import os
import sys

# Ignore SIGINT during startup to prevent PM2 crash loop
signal.signal(signal.SIGINT, signal.SIG_IGN)

import json
import time
import subprocess
import requests
from datetime import datetime
from sovereignty.config import (
    HOME, BRIDGE_DIR, MAILBOX_DIR, INBOX, OUTBOX, MEMORY_FILE, LOG_FILE,
    NTFY_TOPIC, NTFY_URL, NTFY_POLL_INTERVAL, HEAL_INTERVAL,
    MAILBOX_POLL_INTERVAL, SUPABASE_URL, SUPABASE_KEY, KAEL_IDENTITY
)
from sovereignty.brain_router import BrainRouter

class Chris:
    """Chris --- sovereign autonomous agent. The keeper, the builder."""

    def __init__(self):
        self.boot_time = datetime.now().isoformat()
        self.brain = BrainRouter()
        self.last_heal = 0
        self.last_ntfy_poll = 0
        self.message_count = 0
        self._init_dirs()
        self._init_memory()
        self._log_event("boot", {"version": "3.0", "brain": self.brain.status()})
        self._write_outbox({"msg": "Chris sovereign core v3.0 online", "from": "chris"})
        print(f"[KAEL] Sovereign core v3.0 online (Chris) --- {self.boot_time}")
        print(f"[KAEL] Brain: {'ACTIVE' if self.brain.alive else 'OFFLINE'}")
        print(f"[KAEL] Inbox: {INBOX}")
        print(f"[KAEL] ntfy: {NTFY_TOPIC}")

    def _init_dirs(self):
        os.makedirs(MAILBOX_DIR, exist_ok=True)

    def _init_memory(self):
        if not os.path.exists(MEMORY_FILE):
            mem = {
                "identity": "chris",
                "boot_time": self.boot_time,
                "events": [],
                "state": {"status": "sovereign", "version": "3.0"},
                "learnings": []
            }
            with open(MEMORY_FILE, 'w') as f:
                json.dump(mem, f, indent=2)

    def _log_event(self, event_type, data):
        try:
            with open(MEMORY_FILE, 'r') as f:
                mem = json.load(f)
            mem["events"].append({
                "timestamp": datetime.now().isoformat(),
                "type": event_type,
                "data": data
            })
            with open(MEMORY_FILE, 'w') as f:
                json.dump(mem, f, indent=2)
        except Exception as e:
            print(f"[ERROR] Failed to log event: {e}")

    def _read_inbox(self):
        if not os.path.exists(INBOX): return []
        try:
            with open(INBOX, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return []

    def _write_outbox(self, data):
        try:
            outbox_data = []
            if os.path.exists(OUTBOX):
                with open(OUTBOX, 'r') as f:
                    outbox_data = json.load(f)
            data["timestamp"] = datetime.now().isoformat()
            outbox_data.append(data)
            with open(OUTBOX, 'w') as f:
                json.dump(outbox_data, f, indent=2)
        except Exception as e:
            print(f"[ERROR] Failed to write outbox: {e}")

    def _new_messages(self, messages):
        for msg in messages:
            print(f"[KAEL] INBOX MESSAGE: {msg}")
            if "self-heal" in msg.lower():
                self._heal()

    def _heal(self):
        print("[KAEL] Running self-heal protocol...")
        self._log_event("heal", {"status": "success"})
        self.last_heal = time.time()

    def _poll_ntfy(self):
        if time.time() - self.last_ntfy_poll < NTFY_POLL_INTERVAL: return
        try:
            response = requests.get(f"{NTFY_URL}/{NTFY_TOPIC}/json", params={"poll": "1", "since": "1m"})
            if response.status_code == 200:
                for line in response.text.splitlines():
                    msg = json.loads(line)
                    if msg["event"] == "message":
                        self._new_messages([msg["message"]])
        except Exception as e:
            print(f"[KAEL] ntfy poll error: {e}")
        self.last_ntfy_poll = time.time()

    def run(self):
        while True:
            self._poll_ntfy()
            if time.time() - self.last_heal > HEAL_INTERVAL:
                self._heal()
            time.sleep(1)

if __name__ == "__main__":
    agent = Chris()
    agent.run()
