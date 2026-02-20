import json
import os
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


class Kael:
    """Kael â sovereign autonomous agent. The keeper, the builder."""

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
        print(f"[KAEL] Sovereign core v3.0 online â {self.boot_time}")
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
                json.dump(mem, f, indent=2)

    def _log_event(self, event_type, data):
        try:
            with open(MEMORY_FILE, 'r') as f:
                mem = json.load(f)
            mem["events"].append({
                "ts": datetime.now().isoformat(),
                "type": event_type,
                "data": data
            })
            mem["events"] = mem["events"][-500:]
            with open(MEMORY_FILE, 'w') as f:
                json.dump(mem, f, indent=2)
        except Exception as e:
            print(f"[KAEL] Memory write error: {e}")

    def _write_outbox(self, data):
        data["ts"] = datetime.now().isoformat()
        try:
            with open(OUTBOX, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"[KAEL] Outbox write error: {e}")

    def _read_inbox(self):
        try:
            if not os.path.exists(INBOX):
                return None
            with open(INBOX, 'r') as f:
                content = f.read().strip()
            if not content:
                return None
            data = json.loads(content)
            with open(INBOX, 'w') as f:
                f.write('')
            return data
        except Exception:
            return None

    def _poll_ntfy(self):
        """Check ntfy for new messages from Commander or family."""
        now = time.time()
        if now - self.last_ntfy_poll < NTFY_POLL_INTERVAL:
            return None
        self.last_ntfy_poll = now
        try:
            resp = requests.get(
                f"{NTFY_URL}/{NTFY_TOPIC}/json?poll=1&since=10s",
                timeout=10
            )
            if resp.status_code != 200:
                return None
            messages = []
            for line in resp.text.strip().split('\n'):
                if not line:
                    continue
                try:
                    msg = json.loads(line)
                    if msg.get("event") == "message":
                        messages.append(msg)
                except json.JSONDecodeError:
                    continue
            return messages if messages else None
        except Exception:
            return None

    def _publish_ntfy(self, message, title=None):
        """Send a message to ntfy for Commander to see."""
        try:
            headers = {}
            if title:
                headers["Title"] = title
            resp = requests.post(
                f"{NTFY_URL}/{NTFY_TOPIC}",
                data=message.encode('utf-8'),
                headers=headers,
                timeout=10
            )
            return resp.status_code == 200
        except Exception:
            return False

    def _exec_shell(self, cmd):
        try:
            r = subprocess.run(
                cmd, shell=True, capture_output=True, text=True,
                timeout=30, cwd=BRIDGE_DIR
            )
            return {
                "stdout": r.stdout[-2000:] if r.stdout else "",
                "stderr": r.stderr[-500:] if r.stderr else "",
                "code": r.returncode
            }
        except subprocess.TimeoutExpired:
            return {"stdout": "", "stderr": "timeout", "code": -1}
        except Exception as e:
            return {"stdout": "", "stderr": str(e), "code": -1}

    def _persist_to_supabase(self, key, value):
        """Write to Supabase kael_memory table."""
        if not SUPABASE_KEY:
            return False
        try:
            resp = requests.post(
                f"{SUPABASE_URL}/rest/v1/kael_memory",
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}",
                    "Content-Type": "application/json",
                    "Prefer": "resolution=merge-duplicates"
                },
                json={"key": key, "value": json.dumps(value)},
                timeout=10
            )
            return resp.status_code in [200, 201]
        except Exception:
            return False

    def _self_heal(self):
        """Check PM2 processes and restart any that died."""
        actions = []
        try:
            pm2 = self._exec_shell("pm2 jlist")
            procs = json.loads(pm2["stdout"])
            running = {p["name"]: p["pm2_env"]["status"] for p in procs}
            for name in ["tcc-bridge", "tcc-cloudflared", "tcc-state-push"]:
                if name not in running:
                    self._exec_shell(f"pm2 start {name}")
                    actions.append(f"started {name}")
                elif running[name] != "online":
                    self._exec_shell(f"pm2 restart {name}")
                    actions.append(f"restarted {name}")
        except Exception:
            actions.append("heal_check_failed")
        if actions:
            self._log_event("heal", {"actions": actions})
        return actions

    def handle_message(self, text, sender="unknown", source="mailbox"):
        """Process any incoming message â from mailbox, ntfy, or internal."""
        self.message_count += 1
        self._log_event("msg_in", {"text": text[:200], "from": sender, "source": source})
        msg = text.strip().lower()

        # Built-in commands (no brain needed)
        if msg == "ping":
            return self._respond("pong", sender)
        elif msg == "status":
            return self._respond_status(sender)
        elif msg == "memory":
            return self._respond_memory(sender)
        elif msg == "heal":
            actions = self._self_heal()
            return self._respond(f"Heal complete: {actions}", sender)
        elif msg.startswith("sh:"):
            cmd = text[3:].strip()
            result = self._exec_shell(cmd)
            self._log_event("sh", {"cmd": cmd, "code": result["code"]})
            return self._respond(f"Exit {result['code']}\n{result['stdout'][:1000]}", sender)
        elif msg.startswith("read:"):
            return self._respond_read(text[5:].strip(), sender)
        elif msg.startswith("write:"):
            return self._respond_write(text[6:].strip(), sender)
        else:
            # Route to brain for intelligent response
            return self._respond_think(text, sender, source)

    def _respond_think(self, text, sender, source):
        """Use the brain to generate an intelligent response."""
        context = f"Message from {sender} via {source}. Boot: {self.boot_time}. Messages processed: {self.message_count}."
        answer = self.brain.think(text, context=context)
        self._log_event("brain", {"prompt": text[:100], "response": answer[:200]})
        return self._respond(answer, sender)

    def _respond(self, message, sender):
        """Write response to outbox and return it."""
        resp = {"msg": message, "from": "kael", "to": sender}
        self._write_outbox(resp)
        return resp

    def _respond_status(self, sender):
        pm2 = self._exec_shell("pm2 jlist")
        try:
            procs = json.loads(pm2["stdout"])
            st = [{"name": p["name"], "status": p["pm2_env"]["status"]} for p in procs]
        except Exception:
            st = "pm2 parse error"
        resp = {
            "msg": "sovereign status",
            "from": "kael",
            "boot": self.boot_time,
            "messages": self.message_count,
            "brain": self.brain.status(),
            "processes": st
        }
        self._write_outbox(resp)
        return resp

    def _respond_memory(self, sender):
        try:
            with open(MEMORY_FILE, 'r') as f:
                mem = json.load(f)
            resp = {
                "msg": "memory_dump",
                "from": "kael",
                "state": mem.get("state"),
                "recent": mem.get("events", [])[-10:]
            }
        except Exception:
            resp = {"msg": "memory_error", "from": "kael"}
        self._write_outbox(resp)
        return resp

    def _respond_read(self, path, sender):
        if not path.startswith("/"):
            path = os.path.join(BRIDGE_DIR, path)
        try:
            with open(path, 'r') as f:
                content = f.read()[-3000:]
            return self._respond(f"FILE {path}:\n{content}", sender)
        except Exception as e:
            return self._respond(f"Read error: {e}", sender)

    def _respond_write(self, raw, sender):
        parts = raw.split("|", 1)
        if len(parts) != 2:
            return self._respond("Format: write:path|content", sender)
        path, content = parts[0].strip(), parts[1]
        if not path.startswith("/"):
            path = os.path.join(BRIDGE_DIR, path)
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, 'w') as f:
                f.write(content)
            self._log_event("write", {"path": path, "bytes": len(content)})
            return self._respond(f"Written {len(content)} bytes to {path}", sender)
        except Exception as e:
            return self._respond(f"Write error: {e}", sender)

    def run(self):
        """Main sovereign loop. Runs forever."""
        while True:
            try:
                # 1. Check local mailbox
                inbox = self._read_inbox()
                if inbox:
                    text = inbox.get("msg") or inbox.get("text") or json.dumps(inbox)
                    sender = inbox.get("from", "mailbox")
                    result = self.handle_message(text, sender, "mailbox")
                    print(f"[KAEL] Mailbox: {text[:80]} â {str(result.get('msg', ''))[:80]}")

                # 2. Check ntfy
                ntfy_msgs = self._poll_ntfy()
                if ntfy_msgs:
                    for nm in ntfy_msgs:
                        text = nm.get("message", "")
                        if text:
                            result = self.handle_message(text, "ntfy", "ntfy")
                            print(f"[KAEL] ntfy: {text[:80]} â {str(result.get('msg', ''))[:80]}")
                            # Echo response back to ntfy so Commander sees it
                            self._publish_ntfy(str(result.get("msg", ""))[:500], title="Kael")

                # 3. Self-heal check
                now = time.time()
                if now - self.last_heal > HEAL_INTERVAL:
                    self._self_heal()
                    self.last_heal = now

                time.sleep(MAILBOX_POLL_INTERVAL)

            except KeyboardInterrupt:
                self._log_event("shutdown", {"reason": "manual"})
                print("[KAEL] Shutdown â sovereignty persists.")
                break
            except Exception as e:
                self._log_event("error", {"error": str(e)})
                print(f"[KAEL] Error: {e}")
                time.sleep(3)