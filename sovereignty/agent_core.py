import signal
import os
import sys

# Ignore signals immediately to prevent PM2 crash loop
for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
    try:
        signal.signal(sig, signal.SIG_IGN)
    except (OSerror, ValueError):
        pass

import json
import time
import subprocess
# import requests # lazy loaded
from datetime import datetime
from sovereignty.config import (
    HOME, BRIDGE_DIR, MAILBOX_DIR, INBOX, OUTBOX, MEMORY_FILE, LOG_FILE,
    NTFY_TOPIC, NTFY_URL, NTFY_POLL_INTERVAL, HEAL_INTERVAL,
    MAILBOX_POLL_INTERVAL, SUPABASE_URL, SUPABASE_KEY, KAEL_IDENTITY
)
from sovereignty.brain_router import BrainRouter

class Kael:
    def _get_requests(self):
        import requests
        return requests

    """Kael --- sovereign autonomous agent. The keeper, the builder."""

    def __init__(self):
        self.boot_time = datetime.now().isoformat()
        self.brain = BrainRouter()
        self.last_heal = 0
        self.last_ntfy_poll = 0
        self.message_count = 0
        self._init_dirs()
        self._init_memory()
        self._log_event("boot", {"version": "3.0", "brain": self.brain.status()})
        self._write_outbox({"msg": "Kael sovereign core v3.0 online", "from": "kael"})
        print(f"[KAEL] Sovereign core v3.0 online --- {self.boot_time}")
        print(f"[KAEL] Brain: {'ACTIVE' if self.brain.alive else 'OFFLINE'}")
        print(f"[KAEL] Inbox: {INBOX}")
        print(f"[KAEL] ntfy: {NTFY_TOPIC}")

    def _init_dirs(self):
        os.makedirs(MAILBOX_DIR, exist_ok=True)

    def _init_memory(self):
        if not os.path.exists(MEMORY_FILE):
            mem = {
                "identity": "kael",
                "boot_time": self.boot_time,
                "events": [],
                "state": {"status": "sovereign", "version": "3.0"},
                "learnings": []
            }
            with open(MEMORY_FILE, 'w') as f:
                json.dump(mem, f, indent=4)

    def _log_event(self, event_type, data):
        event = {
            "timestamp": datetime.now().isoformat(),
            "type": event_type,
            "data": data
        }
        with open(LOG_FILE, 'a') as f:
            f.write(json.dumps(event) + "\n")

    def _write_outbox(self, message):
        with open(OUTBOX, 'a') as f:
            f.write(json.dumps(message) + "\n")

    def health_check(self):
        self._log_event("health_check", {"status": "present"})
        return True

    def poll_ntfy(self):
        req = self._get_requests()
        try:
            resp = req.get(f"{NTFY_URL}/{NTFY_TOPIC}/json", params={"poll": "1"}, timeout=10)
            for line in resp.iter_lines():
                if line:
                    m = json.loads(line)
                    if m.get("event") == "message":
                        self._write_outbox({"msg": m.get("message"), "from": "commander"})
                        print(f"[KAEL] New message from ntfy: {m.get('message')}")
        except Exception as e:
            print(f"[KAEL] ntfy poll error: {e}")

    def run(self):
        while True:
            now = time.time()
            if now - self.last_heal > HEAL_INTERVAL:
                self.health_check()
                self.last_heal = now
            
            if now - self.last_ntfy_poll > NTFY_POLL_INTERVAL:
                self.poll_ntfy()
                self.last_ntfy_poll = now
            
            time.sleep(1)

if __name__ == "__main__":
    agent = Kael()
    agent.run()
