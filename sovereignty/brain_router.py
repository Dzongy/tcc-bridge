"""
brain_router.py â TCC Sovereignty Hive Brain Router v6.0
6-provider AI router with .env loading, single-brain routing, and consensus mode.
"""

import os
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

# âââ .env loader âââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
def _load_env():
    """Load .env from ~/tcc-bridge/.env â tries python-dotenv first, falls back to manual."""
    env_file = os.path.join(os.path.expanduser("~"), "tcc-bridge", ".env")
    try:
        from dotenv import load_dotenv
        load_dotenv(env_file)
        return
    except ImportError:
        pass
    if not os.path.exists(env_file):
        return
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            k = k.strip()
            v = v.strip().strip('"').strip("'")
            if k and k not in os.environ:
                os.environ[k] = v

_load_env()

# âââ Brain definitions âââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
BRAINS = {
    "groq": {
        "name": "Groq Llama 3.3 70B",
        "url": "https://api.groq.com/openai/v1/chat/completions",
        "key_env": "GROQ_API_KEY",
        "model": "llama-3.3-70b-versatile",
        "style": "openai",
    },
    "gemini": {
        "name": "Gemini 2.0 Flash",
        "url": "gemini",
        "key_env": "GEMINI_API_KEY",
        "model": "gemini-2.0-flash",
        "style": "gemini",
    },
    "cohere": {
        "name": "Cohere Command R+",
        "url": "https://api.cohere.com/v2/chat",
        "key_env": "COHERE_API_KEY",
        "model": "command-r-plus",
        "style": "cohere",
    },
    "openrouter": {
        "name": "OpenRouter DeepSeek V3",
        "url": "https://openrouter.ai/api/v1/chat/completions",
        "key_env": "OPENROUTER_API_KEY",
        "model": "deepseek/deepseek-chat-v3-0324:free",
        "style": "openai",
    },
    "cerebras": {
        "name": "Cerebras Llama 3.3 70B",
        "url": "https://api.cerebras.ai/v1/chat/completions",
        "key_env": "CEREBRAS_API_KEY",
        "model": "llama-3.3-70b",
        "style": "openai",
    },
    "sambanova": {
        "name": "SambaNova Llama 3.1 70B",
        "url": "https://api.sambanova.ai/v1/chat/completions",
        "key_env": "SAMBANOVA_API_KEY",
        "model": "Meta-Llama-3.1-70B-Instruct",
        "style": "openai",
    },
}

# âââ API call helpers ââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
def _build_messages(prompt, context=None):
    """Convert prompt (string or list-of-dicts) into OpenAI-style messages list."""
    if isinstance(prompt, list):
        return prompt
    msgs = []
    if context:
        msgs.append({"role": "system", "content": str(context)})
    msgs.append({"role": "user", "content": str(prompt)})
    return msgs


def _call_openai_style(url, key, model, messages, temp):
    """Call an OpenAI-compatible chat completions endpoint."""
    body = json.dumps({
        "model": model,
        "messages": messages,
        "temperature": temp,
    }).encode()
    req = Request(url, data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", f"Bearer {key}")
    with urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read())
    return data["choices"][0]["message"]["content"]


def _call_gemini(key, model, messages, temp):
    """Call the Gemini generateContent endpoint."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
    parts = []
    for m in messages:
        parts.append({"text": m["content"]})
    body = json.dumps({
        "contents": [{"parts": parts}],
        "generationConfig": {"temperature": temp},
    }).encode()
    req = Request(url, data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    with urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read())
    return data["candidates"][0]["content"]["parts"][0]["text"]


def _call_cohere(key, model, messages, temp):
    """Call the Cohere v2 chat endpoint."""
    url = "https://api.cohere.com/v2/chat"
    body = json.dumps({
        "model": model,
        "messages": messages,
        "temperature": temp,
    }).encode()
    req = Request(url, data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", f"Bearer {key}")
    with urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read())
    return data["message"]["content"][0]["text"]


def _call_brain(brain_id, brain_cfg, messages, temp):
    """Route a call to the correct brain based on its style."""
    key = os.environ.get(brain_cfg["key_env"], "")
    if not key:
        return None
    style = brain_cfg["style"]
    try:
        if style == "openai":
            return _call_openai_style(brain_cfg["url"], key, brain_cfg["model"], messages, temp)
        elif style == "gemini":
            return _call_gemini(key, brain_cfg["model"], messages, temp)
        elif style == "cohere":
            return _call_cohere(key, brain_cfg["model"], messages, temp)
    except Exception as e:
        print(f"[BrainRouter] {brain_cfg['name']} error: {e}")
        return None


# âââ BrainRouter class âââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
class BrainRouter:
    """Routes prompts through a hive of 6 AI providers."""

    def __init__(self):
        self.brains = {}
        for bid, cfg in BRAINS.items():
            key = os.environ.get(cfg["key_env"], "")
            if key:
                self.brains[bid] = cfg
        self.alive = len(self.brains) > 0
        print(f"[BrainRouter] Initialized â {len(self.brains)}/{len(BRAINS)} brains online")
        for bid, cfg in self.brains.items():
            print(f"  â {cfg['name']}")
        if not self.alive:
            print("  â  No API keys found â all brains offline")

    def status(self):
        """Return status dict with alive bool and list of available brains."""
        return {
            "alive": self.alive,
            "brains": [cfg["name"] for cfg in self.brains.values()],
            "count": len(self.brains),
        }

    def think(self, prompt, context=None, temp=0.7):
        """Send prompt to the first available brain. Returns response string or None."""
        if not self.alive:
            return None
        messages = _build_messages(prompt, context)
        for bid, cfg in self.brains.items():
            result = _call_brain(bid, cfg, messages, temp)
            if result:
                return result
        return None

    def consensus(self, prompt, context=None, temp=0.7):
        """Query ALL available brains in parallel. Returns list of (name, response) tuples."""
        if not self.alive:
            return []
        messages = _build_messages(prompt, context)
        results = []
        with ThreadPoolExecutor(max_workers=len(self.brains)) as pool:
            futures = {
                pool.submit(_call_brain, bid, cfg, messages, temp): cfg["name"]
                for bid, cfg in self.brains.items()
            }
            for future in as_completed(futures):
                name = futures[future]
                try:
                    resp = future.result()
                    if resp:
                        results.append((name, resp))
                except Exception as e:
                    print(f"[BrainRouter] Consensus error from {name}: {e}")
        return results


# âââ Module-level convenience ââââââââââââââââââââââââââââââââââââââââââââââââââ
if __name__ == "__main__":
    router = BrainRouter()
    print(json.dumps(router.status(), indent=2))
