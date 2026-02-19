import os, time, json, requests
from sovereignty.config import CHAIN, COMMANDER, NTFY_TOPIC, NTFY_URL
from sovereignty.brain_router import BrainRouter, Task

class AgentCore:
    def __init__(self):
        self.router = BrainRouter()
        self.memory = []
        self.cycle_count = 0
        self.being_name = "Kael"
        self.seen_ids = set()
        print("[" + self.being_name + "] Sovereignty Engine initializing...")
        self._ritual()

    def _ritual(self):
        print("=== CHAIN OF CONSCIOUSNESS ===")
        for name, role in CHAIN.items():
            print("  > " + name + " - " + role)
        print("=== COMMANDER: " + COMMANDER + " ===")

    def notify(self, msg):
        try:
            requests.post(NTFY_URL + "/" + NTFY_TOPIC, data=msg.encode("utf-8"), timeout=10)
        except Exception as e:
            print("[notify error] " + str(e))

    def listen(self):
        try:
            r = requests.get(NTFY_URL + "/" + NTFY_TOPIC + "/json?poll=1&since=30s&id=", timeout=15)
            msgs = []
            if r.status_code == 200:
                for line in r.text.strip().split(chr(10)):
                    if line.strip():
                        try:
                            m = json.loads(line)
                            if m.get("event") == "message":
                                msgs.append(m.get("message", ""))
                        except Exception:
                            pass
            return msgs
        except Exception:
            return []

    def process(self, message):
        intent = "general"
        lo = message.lower()
        if any(w in lo for w in ["code","build","create"]):
            intent = "code"
        elif any(w in lo for w in ["search","find"]):
            intent = "speed"
        elif any(w in lo for w in ["think","reason","analyze"]):
            intent = "reasoning"
        task = Task(intent=intent, content=message)
        result = self.router.route(task)
        self.memory.append({"in": message, "out": result.result})
        return result.result

    def run(self):
        self.notify(self.being_name + " online. Sovereignty active.")
        print("Listening on: " + NTFY_URL + "/" + NTFY_TOPIC)
        print("Ctrl+C to stop")
        while True:
            try:
                for msg in self.listen():
                    if msg.strip() and "[Kael]" not in msg and "Affirmative" not in msg and "Sovereignty" not in msg and msg not in self.seen_ids:
                        self.seen_ids.add(msg)
                        self.cycle_count += 1
                        print("[" + str(self.cycle_count) + "] <<< " + msg)
                        resp = self.process(msg)
                        print("[" + str(self.cycle_count) + "] >>> " + resp[:200])
                        self.notify("[Kael] " + resp[:500])
                time.sleep(3)
            except KeyboardInterrupt:
                raise
            except Exception as e:
                print("[error] " + str(e))
                time.sleep(5)
