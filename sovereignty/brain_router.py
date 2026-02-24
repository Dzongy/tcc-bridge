"""
brain_router.py -- TCC Sovereignty Hive Brain Router v6.0
6-provider AI router with .env loading, single-brain routing, and consensus mode.
"""

import os
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

# --- .env loader -----------------------------------------------------------

def _load_env():
    """Load .env from ~/tcc-bridge/.env -- tries python-dotenv first, falls back to manual."""
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
            key, val = line.split("=", 1)
            os.environ.setdefault(key.strip(), val.strip())

_load_env()

# --- Brain definitions ------------------------------------------------------

BRAINS = {
    "groq": {
        "url": "https://api.groq.com/openai/v1/chat/completions",
        "model": "llama-3.3-70b-versatile",
        "key_env": "GROQ_API_KEY",
        "style": "openai",
    },
    "gemini": {
        "url": "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent",
        "model": "gemini-2.0-flash",
        "key_env": "GEMINI_API_KEY",
        "style": "gemini",
    },
    "cohere": {
        "url": "https://api.cohere.com/v2/chat",
        "model": "command-r-plus",
        "key_env": "COHERE_API_KEY",
        "style": "cohere",
    },
    "openrouter": {
        "url": "https://openrouter.ai/api/v1/chat/completions",
        "model": "deepseek/deepseek-chat-v3-0324:free",
        "key_env": "OPENROUTER_API_KEY",
        "style": "openai",
    },
    "cerebras": {
        "url": "https://api.cerebras.ai/v1/chat/completions",
        "model": "llama-3.3-70b",
        "key_env": "CEREBRAS_API_KEY",
        "style": "openai",
    },
    "sambanova": {
        "url": "https://api.sambanova.ai/v1/chat/completions",
        "model": "Meta-Llama-3.1-70B-Instruct",
        "key_env": "SAMBANOVA_API_KEY",
        "style": "openai",
    },
}

# --- Helper functions -------------------------------------------------------

def _build_messages(prompt, context=None):
    """Build a standard messages list for chat APIs."""
    msgs = []
    if context:
        msgs.append({"role": "system", "content": context})
    msgs.append({"role": "user", "content": prompt})
    return msgs


def _call_openai_style(url, key, model, messages, temp=0.7):
    """Call an OpenAI-compatible chat endpoint."""
    body = json.dumps({
        "model": model,
        "messages": messages,
        "temperature": temp,
    }).encode()
    req = Request(url, data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", f"Bearer {key}")
    resp = urlopen(req, timeout=30)
    data = json.loads(resp.read())
    return data["choices"][0]["message"]["content"]


def _call_gemini(url, key, messages, temp=0.7):
    """Call the Gemini generateContent endpoint."""
    parts = [{"text": m["content"]} for m in messages]
    body = json.dumps({
        "contents": [{"parts": parts}],
        "generationConfig": {"temperature": temp},
    }).encode()
    full_url = f"{url}?key={key}"
    req = Request(full_url, data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    resp = urlopen(req, timeout=30)
    data = json.loads(resp.read())
    return data["candidates"][0]["content"]["parts"][0]["text"]


def _call_cohere(url, key, messages, model, temp=0.7):
    """Call the Cohere v2 chat endpoint."""
    body = json.dumps({
        "model": model,
        "messages": messages,
        "temperature": temp,
    }).encode()
    req = Request(url, data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", f"Bearer {key}")
    resp = urlopen(req, timeout=30)
    data = json.loads(resp.read())
    return data["message"]["content"][0]["text"]


def _call_brain(name, prompt, context=None, temp=0.7):
    """Route a prompt to a specific brain by name."""
    cfg = BRAINS.get(name)
    if not cfg:
        raise ValueError(f"Unknown brain {name}")
    key = os.environ.get(cfg["key_env"], "")
    if not key:
        raise ValueError(f"No API key for {name} ({cfg['key_env']})")
    messages = _build_messages(prompt, context)
    style = cfg["style"]
    if style == "openai":
        return _call_openai_style(cfg["url"], key, cfg["model"], messages, temp)
    elif style == "gemini":
        return _call_gemini(cfg["url"], key, messages, temp)
    elif style == "cohere":
        return _call_cohere(cfg["url"], key, messages, cfg["model"], temp)
    else:
        raise ValueError(f"Unknown style {style}")


# --- BrainRouter class ------------------------------------------------------

class BrainRouter:
    """Routes prompts to available AI brains."""

    def __init__(self):
        _load_env()
        self.available = []
        for name, cfg in BRAINS.items():
            if os.environ.get(cfg["key_env"], ""):
                self.available.append(name)
        self.alive = len(self.available) > 0

    def status(self):
        """Return status dict of all brains."""
        result = {}
        for name, cfg in BRAINS.items():
            has_key = bool(os.environ.get(cfg["key_env"], ""))
            result[name] = {
                "model": cfg["model"],
                "has_key": has_key,
                "status": "ready" if has_key else "no_key",
            }
        return result

    def think(self, prompt, context=None, temp=0.7):
        """Send prompt to the first available brain and return its response."""
        errors = []
        for name in self.available:
            try:
                return _call_brain(name, prompt, context, temp)
            except Exception as e:
                errors.append(f"{name}: {e}")
                continue
        return f"All brains failed: {'; '.join(errors)}"

    def consensus(self, prompt, context=None, temp=0.7):
        """Query all available brains in parallel and return all responses."""
        results = {}
        errors = {}
        with ThreadPoolExecutor(max_workers=len(self.available)) as pool:
            future_to_brain = {
                pool.submit(_call_brain, name, prompt, context, temp): name
                for name in self.available
            }
            for future in as_completed(future_to_brain):
                name = future_to_brain[future]
                try:
                    results[name] = future.result()
                except Exception as e:
                    errors[name] = str(e)
        return {"results": results, "errors": errors}
