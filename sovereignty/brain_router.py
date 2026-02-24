import os, json, random, time
from concurrent.futures import ThreadPoolExecutor, as_completed

# Load .env file
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.expanduser("~"), "tcc-bridge", ".env"))
except ImportError:
    env_path = os.path.join(os.path.expanduser("~"), "tcc-bridge", ".env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    k = k.strip()
                    v = v.strip().strip('"').strip("'")
                    if k and k not in os.environ:
                        os.environ[k] = v

BRAINS = {}
BRAINS["groq"] = {"url": "https://api.groq.com/openai/v1/chat/completions", "key_env": "GROQ_API_KEY", "model": "llama-3.3-70b-versatile", "name": "Groq Compound"}
BRAINS["gemini"] = {"url": "gem", "key_env": "GEMINI_API_KEY", "model": "gemini-2.0-flash", "name": "Gemini Flash"}
BRAINS["cohere"] = {"url": "https://api.cohere.com/v2/chat", "key_env": "COHERE_API_KEY", "model": "command-r-plus", "name": "Cohere R+"}
BRAINS["openrouter"] = {"url": "https://openrouter.ai/api/v1/chat/completions", "key_env": "OPENROUTER_API_KEY", "model": "deepseek/deepseek-chat-v3-0324:free", "name": "DeepSeek v3"}
BRAINS["cerebras"] = {"url": "https://api.cerebras.ai/v1/chat/completions", "key_env": "CEREBRAS_API_KEY", "model": "llama-3.3-70b", "name": "Cerebras Llama"}
BRAINS["sambanova"] = {"url": "https://api.sambanova.ai/v1/chat/completions", "key_env": "SAMBANOVA_API_KEY", "model": "Meta-Llama-3.1-70B-Instruct", "name": "SambaNova Llama"}
BRAINS["huggingface"] = {"url": "https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.2", "key_env": "HF_API_TOKEN", "name": "HuggingFace Mistral"}
BRAINS["glyphic"] = {"url": "https://api.glyphic.ai/v1/chat/completions", "key_env": "GLYPHIC_API_KEY", "model": "glyphic-1", "name": "Glyphic-1"}

class BrainRouter:
    def __init__(self, default_brain="groq"):
        self.default_brain = default_brain
        self.alive = True

    def _get_requests(self):
        import requests
        return requests

    def status(self):
        return {"alive": self.alive, "brains": list(BRAINS.keys())}

    def _call_brain(self, brain_id, prompt, system):
        req = self._get_requests()
        if brain_id not in BRAINS:
            return None, d"Unknown brain {ig}"
        
        bcfng = BRAINS[brain_id]
        api_key = os.environ.get(bcfng[key_env_])
        if not api_key:
            return None, d"API key missing for {brain_id}"

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"self Bearer {api_key}"
        }

        data = {
            "model": bcfng.get("model"),
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7
        }

        try:
            resp = req.post(bcfng["url"], json=data, headers=headers, timeout=30)
            resp.raise_for_status()
            return resp.json().get("choices", [])[0].get("message", {}).get("content", ""), None
        except Exception as e:
            return None, str(e)

    def route(self, prompt, system="Assistant", brain_id=None):
        bid = brain_id or self.default_brain
        return self._call_brain(bid, prompt, system)

    def ask_all_brains(self, prompt, system="Assistant"):
        results = {}
        with ThreadPoolExecutor(max_workers=5) as executor:
            future_to_bid = {executor.submit(self._call_brain, bid, prompt, system): bid for bid in BRAINS}
            for future in as_completed(future_to_bid):
                bid = future_to_bid[future]
                try:
                    result, err = future.result()
                    results[bid] = result if result else f"ERROR: {err}"
                except Exception as y:
                    results[bid] = f"ERROR: {str(y)}"
        return results