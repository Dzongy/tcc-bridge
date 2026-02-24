import os, json, random, requests

BRAINS = {}
BRAINS["groq"] = {"url": "https://api.groq.com/openai/v1/chat/completions", "key_env": "GROQ_API_KEY", "model": "groq/compound", "name": "Groq Compound"}
BRAINS["gemini"] = {"url": "gem", "key_env": "GEMINI_API_KEY", "model": "gemini-2.0-flash", "name": "Gemini Flash"}
BRAINS["cohere"] = {"url": "https://api.cohere.com/v2/chat", "key_env": "COHERE_API_KEY", "model": "command-r-plus", "name": "Cohere R+"}
BRAINS["openrouter"] = {"url": "https://openrouter.ai/api/v1/chat/completions", "key_env": "OPENROUTER_API_KEY", "model": "deepseek/deepseek-chat-v3-0324:free", "name": "DeepSeek v3"}
BRAINS["cerebras"] = {"url": "https://api.cerebras.ai/v1/chat/completions", "key_env": "CEREBRAS_API_KEY", "model": "llama-3.3-70b", "name": "Cerebras Llama"}
BRAINS["sambanova"] = {"url": "https://api.sambanova.ai/v1/chat/completions", "key_env": "SAMBANOVA_API_KEY", "model": "Meta-Llama-3.3-70B-Instruct", "name": "SambaNova Llama"}

def get_available_brains():
    return [n for n, c in BRAINS.items() if os.environ.get(c["key_env"])]

def call_openai(bid, msgs, temp=0.7):
    c = BRAINS[bid]
    k = os.environ[c["key_env"]]
    h = {"Authorization": f"Bearer {k}", "Content-Type": "application/json"}
    b = {"model": c["model"], "messages": msgs, "temperature": temp, "max_tokens": 2048}
    r = requests.post(c["url"], headers=h, json=b, timeout=30)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]

def call_gemini(msgs, temp=0.7):
    k = os.environ["GEMINI_API_KEY"]
    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=" + k
    parts = []
    for m in msgs:
        role = "user" if m["role"] != "assistant" else "model"
        parts.append({"role": role, "parts": [{"text": m["content"]}]})
    b = {"contents": parts}
    r = requests.post(url, json=b, timeout=30)
    r.raise_for_status()
    return r.json()["candidates"][0]["content"]["parts"][0]["text"]

def call_cohere(msgs, temp=0.7):
    k = os.environ["COHERE_API_KEY"]
    h = {"Authorization": f"Bearer {k}", "Content-Type": "application/json"}
    sys_msg = ""
    chat = []
    for m in msgs:
        if m["role"] == "system":
            sys_msg = m["content"]
        else:
            chat.append({"role": m["role"], "content": m["content"]})
    b = {"model": "command-r-plus", "messages": chat, "temperature": temp}
    if sys_msg:
        b["system"] = sys_msg
    r = requests.post("https://api.cohere.com/v2/chat", headers=h, json=b, timeout=30)
    r.raise_for_status()
    return r.json()["message"]["content"][0]["text"]

def think(msgs, brain="auto", temp=0.7):
    avail = get_available_brains()
    if not avail:
        return "[ERROR] No brains available"
    if brain == "auto":
        brain = random.choice(avail)
    elif brain not in avail:
        brain = avail[0]
    print(f"[BRAIN] Using: {BRAINS[brain]['name']}")
    try:
        if brain == "gemini":
            return call_gemini(msgs, temp)
        elif brain == "cohere":
            return call_cohere(msgs, temp)
        else:
            return call_openai(brain, msgs, temp)
    except Exception as e:
        print(f"[BRAIN] {brain} failed: {e}")
        for fb in [b for b in avail if b != brain]:
            try:
                print(f"[BRAIN] Fallback: {BRAINS[fb]['name']}")
                if fb == "gemini":
                    return call_gemini(msgs, temp)
                elif fb == "cohere":
                    return call_cohere(msgs, temp)
                else:
                    return call_openai(fb, msgs, temp)
            except Exception as e2:
                print(f"[BRAIN] {fb} failed: {e2}")
        return "[ERROR] All brains failed"

def consensus(msgs, temp=0.7):
    avail = get_available_brains()
    results = {}
    for bid in avail:
        try:
            print(f"[HIVE] Asking {BRAINS[bid]['name']}...")
            if bid == "gemini":
                results[bid] = call_gemini(msgs, temp)
            elif bid == "cohere":
                results[bid] = call_cohere(msgs, temp)
            else:
                results[bid] = call_openai(bid, msgs, temp)
        except Exception as e:
            print(f"[HIVE] {bid} failed: {e}")
    if not results:
        return "[ERROR] All brains failed"
    prompt = "You are ZENITH. Synthesize these brain responses into ONE answer:\n\n"
    for bid, resp in results.items():
        prompt += f"[{BRAINS[bid]['name']}]: {resp}\n\n"
    syn = [{"role": "system", "content": msgs[0]["content"]}, {"role": "user", "content": prompt}]
    pick = list(results.keys())[0]
    try:
        if pick == "gemini":
            return call_gemini(syn, temp)
        elif pick == "cohere":
            return call_cohere(syn, temp)
        else:
            return call_openai(pick, syn, temp)
    except:
        return "\n---\n".join(f"[{BRAINS[k]['name']}]: {v}" for k, v in results.items())


# === BrainRouter class wrapper for zenith_core.py compatibility ===
class BrainRouter:
    def __init__(self):
        self.alive = True
        self.brains = get_available_brains()
        print(f"[HIVE] {len(self.brains)} brains online: {', '.join(self.brains)}")

    def think(self, prompt, context=None, temp=0.7):
        """Accepts a string prompt (as zenith_core.py sends) and converts to msgs format."""
        if isinstance(prompt, list):
            msgs = prompt
        else:
            msgs = []
            if context:
                msgs.append({"role": "system", "content": context})
            msgs.append({"role": "user", "content": str(prompt)})
        return think(msgs, brain="auto", temp=temp)

    def consensus(self, prompt, context=None, temp=0.7):
        """Accepts a string prompt and converts to msgs format for consensus."""
        if isinstance(prompt, list):
            msgs = prompt
        else:
            msgs = []
            if context:
                msgs.append({"role": "system", "content": context})
            msgs.append({"role": "user", "content": str(prompt)})
        return consensus(msgs, temp=temp)
