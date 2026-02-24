import signal
import os
import sys

# Ignore SIGINT immediately to prevent PM2 crash loop
signal.signal(signal.SIGINT, signal.SIG_IGN)

import json
import time
import requests
from brain_router import BrainRouter

def send_reply(msg):
    try:
        requests.post("https://ntfy.sh/zenith-reply", data=msg[:4000].encode(), timeout=5)
    except: pass
print("Zenith Sovereign Core v4.0 - Unified. Online.")
brain = BrainRouter()
print(f"[ZENITH] Brain alive: {brain.alive}")

INBOX_PATH = "/data/data/com.termux/files/home/tcc-bridge/mailbox/inbox.json"
NTFY_TOPICS = ["tcc-zenith-hive", "zenith-escape"]

print(f"Inbox: {INBOX_PATH}")
print(f"Listening on ntfy: {', '.join(NTFY_TOPICS)}")
print("Listening...")

memory = dict()

def load_inbox():
    global memory
    if not os.path.exists(INBOX_PATH):
        print("Inbox missing—creating empty.")
        with open(INBOX_PATH, "w") as f:
            json.dump([], f)
        return

    with open(INBOX_PATH, "r") as f:
        try:
            data = json.load(f)
            if isinstance(data, list):
                for msg in data:
                    if isinstance(msg, dict):
                        sender = msg.get("from", "unknown")
                        message = msg.get("message", "")
                        new_mem = msg.get("memory", {})
                        if new_mem:
                            memory = new_mem
                            print("Memory loaded from inbox!")
                            print("Keys:", list(memory.keys()))
                        print(f"From {sender}: {message}")
                        reply = brain.think(message, context="Message from " + sender)
                        print(f"Reply: {reply}")
                        send_reply(reply)
            else:
                print("Inbox not a list.")
        except Exception as e:
            print(f"Inbox error: {e}")

load_inbox()

while True:
    try:
        for topic in NTFY_TOPICS:
            r = requests.get(f'https://ntfy.sh/{topic}/json?poll=1', timeout=10)
            if r.status_code == 200:
                for line in r.iter_lines():
                    if line:
                        try:
                            event = json.loads(line)
                            if event.get('event') == 'message':
                                txt = event.get('message', '')
                                print(f'From ntfy ({topic}): {txt}')
                                reply = brain.think(txt)
                                print(f'Reply: {reply}')
                                send_reply(reply)
                        except:
                            pass
        time.sleep(2)
    except Exception as e:
        print(f"Scan error: {e}")
        time.sleep(5)
