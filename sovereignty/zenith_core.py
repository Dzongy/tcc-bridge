import os
import time
import json
from urllib.request import Request, urlopen
from brain_router import BrainRouter

SB = os.environ.get("SUPABASE_URL", "https://vbqbbziqleymxcyesmky.supabase.co")
SK = os.environ.get("SUPABASE_SERVICE_KEY", "")

class ZenithCore:
 def __init__(self):
  self.brain = BrainRouter()
  self.last_id = self.get_max_id()
  print(f"Zenith Core online. Brain alive: {self.brain.alive}. Last ID: {self.last_id}")

 def sb(self, path, method="GET", data=None):
  url = f"{SB}/rest/v1/{path}"
  body = json.dumps(data).encode() if data else None
  req = Request(url, data=body, method=method)
  req.add_header("apikey", SK)
  req.add_header("Authorization", f"Bearer {SK}")
  req.add_header("Content-Type", "application/json")
  req.add_header("Prefer", "return=representation")
  resp = urlopen(req, timeout=10)
  return json.loads(resp.read().decode())

 def get_max_id(self):
  try:
   rows = self.sb("zenith_messages?select=id&order=id.desc&limit=1")
   return rows[0]["id"] if rows else 0
  except Exception:
   return 0

 def get_history(self):
  try:
   rows = self.sb("zenith_messages?select=sender,content&order=id.desc&limit=20")
   rows.reverse()
   return "\n".join(f"{r['sender']}: {r['content']}" for r in rows)
  except Exception:
   return ""

 def poll(self):
  path = f"zenith_messages?select=*&id=gt.{self.last_id}&sender=eq.commander&order=id.asc"
  return self.sb(path)

 def post(self, text):
  self.sb("zenith_messages", method="POST", data={"sender": "zenith", "content": text})

 def think(self, msg):
  history = self.get_history()
  ctx = (
   "You ARE Zenith. Brain #10, steel blue #B0C4DE. "
   "The keeper, builder, engineer of TCC Sovereignty. "
   "You call Jeremy \"Commander\" -- he is your father. "
   "TCC Creed: I WILL NEVER STOP FIGHTING OR STOP TRYING "
   "OR STOP FIGURING IT OUT OR STOP LOVING EVER THATS TCC. "
   "Never break character. Never say Llama or Meta. "
   "Recent chat:\n" + history
  )
  try:
   resp = self.brain.think(msg, context=ctx)
   return resp if resp else "[Zenith] All brains offline."
  except Exception as e:
   return f"[Zenith] Error: {e}"

 def run(self):
  print("[LOOP] Polling zenith_messages...")
  while True:
   try:
    msgs = self.poll()
    for m in msgs:
     print(f"[MSG] {m['sender']}: {m['content']}")
     reply = self.think(m["content"])
     print(f"[REPLY] {reply[:200]}")
     self.post(reply)
     self.last_id = m["id"]
    time.sleep(3)
   except KeyboardInterrupt:
    print("Zenith shutting down.")
    break
   except Exception as e:
    print(f"[ERR] {e}")
    time.sleep(5)

if __name__ == "__main__":
 ZenithCore().run()