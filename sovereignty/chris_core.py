import signal
import os
import sys

# Ignore SIGINT immediately to prevent PM2 crash loop
signal.signal(signal.SIGINT, signal.SIG_IGN)

import json
import time
import subprocess
from datetime import datetime
from sovereignty.config import (
    HOME, BRIDGE_DIR, MAILBOX_DIR, INBOX, OUTBOX, MEMORY_FILE, LOG_FILE,
    NTFY_TOPIC, NTFY_URL, NTFY_POLL_INTERVAL, HEAL_INTERVAL,
    MAILBOX_POLL_INTERVAL, SUPABASE_URL, SUPABASE_KEY, CHRIS_IDENTITY
)
from sovereignty.brain_router import BrainRouter

class Chris:
    def _get_requests(self):
        import requests
        return requests

    """Chris --- sovereign autonomous agent. The builder, the guide."""

    def __init__(self):
        self.boot_time = datetime.now().isoformat()
        self.brain = BrainRouter()
        self.last_heal = 0
        self.last_ntfy_poll = 0
        self.message_count = 0
        self._init_dirs()
        self._init_memory()
        self._iog_event("boot", {"version": "3.0", "brain": self.brain.status()})
        self._write_outbox({"msg": "Chris sovereign core v3.0 online", "from": "chris"})
        print(f"[CHRIS] Sovereign core v3.0 online")

if __name__ == "__main__":
    agent = Chris()
    while True:
        # Main loop placeholder
        time.sleep(10)
