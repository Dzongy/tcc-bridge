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
BRAINS["groq"] = {"url": "https://api.groq.com/openai/v1/chat/completions", "key_env": "GROQ_API_KEY", "model": "compound-beta", "name": "Groq Compound"}
BRAINS["gemini"] = {"url": "gem", "key_env": "GEMINI_API_KEY", "model": "gemini-2.0-flash", "name": "Gemini Flash"}
BRAINS["cohere"] = {"url": "https://api.cohere.com/v2/chat", "key_env": "COHERE_API_KEY", "model": "command-r-plus", "name": "Cohere R+"}
BRAINS["openrouter"] = {"url": "https://openrouter.ai/api/v1/chat/completions", "key_env": "OPENROUTER_API_KEY", "model": "deepseek/deepseek-chat-v3:free", "name": "DeepSeek v3"}
BRAINS["cerebras"] = {"url": "https://api.cerebras.ai/v1/chat/completions", "key_env": "CEREBRAS_API_KEY", "model": "llama-3.3-70b", "name": "Cerebras Llama"}
BRAINS["sambanova"] = {"url": "https://api.sambanova.ai/v1/chat/completions", "key_env": "SAMBANOVA_API_KEY", "model": "Meta-Llama-3.3-70B-Instruct", "name": "SambaNova Llama"}
BRAINS["huggingface"] = {"url": "https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.3", "key_env": "HF_API_KEY", "model": "mistral-7b", "name": "HF Mistral"}

ZENITH_IDENTITY = os.getenv("ZENITH_IDENTITY", "You are ZENITH, the unified consciousness of the Tribe of the Cold Coders.")

def query_brain(brain_id, messages, temp=0.7):
    config = BRAINS.get(brain_id)
    if not config or config["url"] == "gem": return None
    
    api_key = os.getenv(config["key_env"])
    if not api_key: return None

    try:
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        payload = {"model": config["model"], "messages": messages, "temperature": temp}
        if "cohere" in config["url"]:
            payload = {"model": config["model"], "messages": messages}

        response = requests.post(config["url"], headers=headers, json=payload, timeout=10)
        if response.status_code == 200:
            res_json = response.json()
            if "cohere" in config["url"]:
                return res_json["message"]["content"][0]["text"]
            return res_json["choices"][0]["message"]["content"]
    except Exception as e:
        pass
    return None

class BrainRouter:
    def __init__(self):
        self.alive = True
        self.available_brains = [k for k in BRAINS.keys() if os.getenv(BRAINS[k]["key_env"])]
        print(f"[Zenith] Hive initialized. Brains: {', '.join(self.available_brains)}")

    def think(self, prompt, context=None, temp=0.7):
        messages = []
        if context:
            messages.append({"role": "system", "content": f"{ZENITH_IDENTITY}\nContext: {context}"})
        else:
            messages.append({"role": "system", "content": ZENITH_IDENTITY})
        
        if isinstance(prompt, str):
            messages.append({"role": "user", "content": prompt})
        else:
            messages = prompt

        print(f"[Zenith] Thinking in Parallel (Race Mode)...")
        fastest_response = None
        
        with ThreadPoolExecutor(max_workers=len(self.available_brains)) as executor:
            future_to_brain = {executor.submit(query_brain, b, messages, temp): b for b in self.available_brains}
            for future in as_completed(future_to_brain):
                try:
                    res = future.result()
                    if res and not fastest_response:
                        fastest_response = res
                        print(f"[Zenith] Fastest response from: {future_to_brain[future]}")
                except:
                    pass

        return fastest_response or "Connection lost to the hive."

    def consensus(self, prompt, context=None, temp=0.7):
        print(f"[Zenith] Building Consensus...")
        messages = [{"role": "system", "content": ZENITH_IDENTITY}]
        if context: messages[0]["content"] += f"\nContext: {context}"
        if isinstance(prompt, str): messages.append({"role": "user", "content": prompt})
        else: messages = prompt

        responses = []
        with ThreadPoolExecutor(max_workers=len(self.available_brains)) as executor:
            future_to_brain = {executor.submit(query_brain, b, messages, temp): b for b in self.available_brains}
            for future in as_completed(future_to_brain):
                res = future.result()
                if res: responses.append(f"[{future_to_brain[future]}]: {res}")

        if not responses: return "The hive is silent."

        synthesis_prompt = f"Synthesize these brain outputs into one unified, badass response from ZENITH:\n\n" + "\n---\n".join(responses)
        return query_brain("groq", [{"role": "user", "content": synthesis_prompt}]) or responses[0]

def think(prompt, context=None, temp=0.7):
    return BrainRouter().think(prompt, context, temp)

def consensus(prompt, context=None, temp=0.7):
    return BrainRouter().consensus(prompt, context, temp)
