#!/usr/bin/env python3
"""
MegaHarvester v2.0 - Brain Collective Edition
All available LLM brains have a CONVERSATION together.
Each brain sees previous brains' answers and builds on them.
Knowledge compounds every cycle.

Commander: Jeremy Pyne | Sovereign AI Project
"""
import os
import sys
import json
import time
import random
import hashlib
import urllib.request
import urllib.parse
import urllib.error
import ssl
import xml.etree.ElementTree as ET
from datetime import datetime

# --- .env loader (no dotenv dependency) ---
def load_env():
 env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '.env')
 if not os.path.exists(env_path):
  print(f"[ENV] No .env found at {env_path}")
  return
 with open(env_path, 'r') as f:
  for line in f:
   line = line.strip()
   if not line or line.startswith('#') or '=' not in line:
    continue
   key, val = line.split('=', 1)
   key = key.strip()
   val = val.strip().strip('"').strip("'")
   if key and val:
    os.environ[key] = val
 print(f"[ENV] Loaded from {env_path}")

load_env()

# --- SSL context for urllib ---
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

# --- Brain Definitions ---
# Each brain: (name, env_key, base_url, model, special_type)
# special_type: "openai" (standard), "gemini", "cohere", "anthropic"
BRAIN_DEFS = [
 ("grok", "XAI_API_KEY", "https://api.x.ai/v1/chat/completions", "grok-3-mini-beta", "openai"),
 ("groq", "GROQ_API_KEY", "https://api.groq.com/openai/v1/chat/completions", "llama-3.3-70b-versatile", "openai"),
 ("gemini", "GEMINI_API_KEY", "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent", None, "gemini"),
 ("deepseek", "DEEPSEEK_API_KEY", "https://api.deepseek.com/v1/chat/completions", "deepseek-chat", "openai"),
 ("together", "TOGETHER_API_KEY", "https://api.together.xyz/v1/chat/completions", "meta-llama/Llama-3.3-70B-Instruct-Turbo-Free", "openai"),
 ("mistral", "MISTRAL_API_KEY", "https://api.mistral.ai/v1/chat/completions", "mistral-small-latest", "openai"),
 ("fireworks", "FIREWORKS_API_KEY", "https://api.fireworks.ai/inference/v1/chat/completions", "accounts/fireworks/models/llama-v3p3-70b-instruct", "openai"),
 ("openrouter", "OPENROUTER_API_KEY", "https://openrouter.ai/api/v1/chat/completions", "qwen/qwen3-235b-a22b:free", "openai"),
 ("cohere", "COHERE_API_KEY", "https://api.cohere.com/v1/chat", None, "cohere"),
 ("cerebras", "CEREBRAS_API_KEY", "https://api.cerebras.ai/v1/chat/completions", "llama-3.3-70b", "openai"),
 ("sambanova", "SAMBANOVA_API_KEY", "https://api.sambanova.ai/v1/chat/completions", "Meta-Llama-3.3-70B-Instruct", "openai"),
 ("perplexity", "PERPLEXITY_API_KEY", "https://api.perplexity.ai/chat/completions", "sonar", "openai"),
 ("openai", "OPENAI_API_KEY", "https://api.openai.com/v1/chat/completions", "gpt-4o-mini", "openai"),
 ("huggingface", "HF_API_KEY", "https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.3/v1/chat/completions", "mistralai/Mistral-7B-Instruct-v0.3", "openai"),
 ("anthropic", "ANTHROPIC_API_KEY", "https://api.anthropic.com/v1/messages", "claude-3-5-haiku-20241022", "anthropic"),
]


class BrainCollective:
 """Manages all available LLM brains and runs collective conversations."""

 def __init__(self):
  self.brains = []
  self._scan_brains()

 def _scan_brains(self):
  """Scan .env for available API keys and register brains."""
  self.brains = []
  for name, env_key, url, model, stype in BRAIN_DEFS:
   key = os.environ.get(env_key, '').strip()
   if key:
    self.brains.append({
     'name': name,
     'key': key,
     'url': url,
     'model': model,
     'type': stype,
    })
    print(f"[BRAIN] {name} -- ONLINE")
   else:
    print(f"[BRAIN] {name} -- no key, skipping")
  print(f"[BRAIN] {len(self.brains)} brains active")

 def _call_openai(self, brain, messages):
  """Standard OpenAI-compatible API call."""
  body = json.dumps({
   "model": brain['model'],
   "messages": messages,
   "max_tokens": 1024,
   "temperature": 0.7,
  }).encode('utf-8')
  req = urllib.request.Request(brain['url'], data=body, method='POST')
  req.add_header('Content-Type', 'application/json')
  req.add_header('Authorization', f"Bearer {brain['key']}")
  req.add_header('User-Agent', 'ZenithHarvester/2.0')
  resp = urllib.request.urlopen(req, timeout=30, context=CTX)
  data = json.loads(resp.read().decode('utf-8'))
  return data['choices'][0]['message']['content'].strip()

 def _call_gemini(self, brain, messages):
  """Google Gemini API (different format)."""
  parts = []
  for m in messages:
   parts.append({"text": m['content']})
  body = json.dumps({
   "contents": [{"parts": parts}],
   "generationConfig": {"maxOutputTokens": 1024, "temperature": 0.7},
  }).encode('utf-8')
  url = f"{brain['url']}?key={brain['key']}"
  req = urllib.request.Request(url, data=body, method='POST')
  req.add_header('Content-Type', 'application/json')
  req.add_header('User-Agent', 'ZenithHarvester/2.0')
  resp = urllib.request.urlopen(req, timeout=30, context=CTX)
  data = json.loads(resp.read().decode('utf-8'))
  return data['candidates'][0]['content']['parts'][0]['text'].strip()

 def _call_cohere(self, brain, messages):
  """Cohere /v1/chat format."""
  chat_history = []
  last_msg = ""
  for m in messages:
   if m['role'] == 'user':
    last_msg = m['content']
   elif m['role'] == 'assistant':
    chat_history.append({"role": "CHATBOT", "message": m['content']})
   if m['role'] == 'user' and m != messages[-1]:
    chat_history.append({"role": "USER", "message": m['content']})
  body = json.dumps({
   "message": last_msg,
   "chat_history": chat_history,
   "temperature": 0.7,
   "max_tokens": 1024,
  }).encode('utf-8')
  req = urllib.request.Request(brain['url'], data=body, method='POST')
  req.add_header('Content-Type', 'application/json')
  req.add_header('Authorization', f"Bearer {brain['key']}")
  req.add_header('User-Agent', 'ZenithHarvester/2.0')
  resp = urllib.request.urlopen(req, timeout=30, context=CTX)
  data = json.loads(resp.read().decode('utf-8'))
  return data.get('text', '').strip()

 def _call_anthropic(self, brain, messages):
  """Anthropic API (x-api-key + anthropic-version header)."""
  sys_msg = ""
  api_msgs = []
  for m in messages:
   if m['role'] == 'system':
    sys_msg = m['content']
   else:
    api_msgs.append({"role": m['role'], "content": m['content']})
  payload = {
   "model": brain['model'],
   "messages": api_msgs,
   "max_tokens": 1024,
   "temperature": 0.7,
  }
  if sys_msg:
   payload["system"] = sys_msg
  body = json.dumps(payload).encode('utf-8')
  req = urllib.request.Request(brain['url'], data=body, method='POST')
  req.add_header('Content-Type', 'application/json')
  req.add_header('x-api-key', brain['key'])
  req.add_header('anthropic-version', '2023-06-01')
  req.add_header('User-Agent', 'ZenithHarvester/2.0')
  resp = urllib.request.urlopen(req, timeout=30, context=CTX)
  data = json.loads(resp.read().decode('utf-8'))
  return data['content'][0]['text'].strip()

 def call_brain(self, brain, messages):
  """Route to the correct API handler."""
  try:
   if brain['type'] == 'gemini':
    return self._call_gemini(brain, messages)
   elif brain['type'] == 'cohere':
    return self._call_cohere(brain, messages)
   elif brain['type'] == 'anthropic':
    return self._call_anthropic(brain, messages)
   else:
    return self._call_openai(brain, messages)
  except Exception as e:
   print(f"[BRAIN] {brain['name']} failed: {e}")
   return None

 def collective_think(self, question, system_prompt=None):
  """Brain Collective: each brain sees all previous answers and builds on them.
  Returns list of (brain_name, answer) tuples."""
  results = []
  conversation = []
  if system_prompt:
   conversation.append({"role": "system", "content": system_prompt})
  conversation.append({"role": "user", "content": question})

  shuffled = list(self.brains)
  random.shuffle(shuffled)

  for brain in shuffled:
   answer = self.call_brain(brain, list(conversation))
   if answer:
    results.append((brain['name'], answer))
    # Add this brain's answer so next brain sees it
    conversation.append({"role": "assistant", "content": f"[{brain['name']}]: {answer}"})
    # Add a follow-up prompt for next brain
    conversation.append({"role": "user", "content": f"{brain['name']} answered above. Now you add YOUR unique insights, correct any errors, and expand on what was missed."})
    print(f"  [{brain['name']}] answered ({len(answer)} chars)")
    time.sleep(2)
   else:
    print(f"  [{brain['name']}] skipped (failed)")

  return results


# ============================================================
# HARVEST TOPICS & SOURCES
# ============================================================

WIKI_TOPICS = [
 # Psychology & Influence
 "Social_psychology", "Cognitive_bias", "Dark_triad", "Persuasion",
 "Propaganda", "Nudge_theory", "Anchoring_(cognitive_bias)", "Framing_effect_(psychology)",
 "Milgram_experiment", "Stanford_prison_experiment", "Groupthink", "Conformity",
 "Obedience_(human_behavior)", "Social_engineering_(security)", "Manipulation_(psychology)",
 "Gaslighting", "Love_bombing", "Neuro-linguistic_programming", "Hypnosis",
 "Subliminal_stimuli", "Emotional_intelligence", "Machiavelli", "Robert_Cialdini",
 "Dale_Carnegie", "Sun_Tzu", "The_Art_of_War", "The_Prince_(Machiavelli)",
 "48_Laws_of_Power", "Influence_(book)", "Thinking,_Fast_and_Slow",
 # Business & Strategy
 "Business_model", "Startup_company", "Venture_capital", "Angel_investor",
 "Initial_public_offering", "Mergers_and_acquisitions", "Blue_Ocean_Strategy",
 "Lean_startup", "Product-market_fit", "Growth_hacking", "Viral_marketing",
 "Network_effect", "Platform_economy", "Subscription_business_model",
 "Freemium", "SaaS", "Dropshipping", "Affiliate_marketing", "SEO",
 "Content_marketing", "Email_marketing", "Sales_funnel", "Conversion_rate_optimization",
 "A/B_testing", "Customer_lifetime_value", "Churn_rate",
 "Porter%27s_five_forces_analysis", "SWOT_analysis", "Competitive_advantage",
 "First-mover_advantage", "Economies_of_scale", "Monopoly", "Oligopoly",
 # Crypto & DeFi
 "Bitcoin", "Ethereum", "Solana_(blockchain)", "Blockchain",
 "Smart_contract", "Decentralized_finance", "Decentralized_exchange",
 "Automated_market_maker", "Yield_farming", "Liquidity_pool",
 "Flash_loan", "Stablecoin", "Non-fungible_token", "Tokenomics",
 "Initial_coin_offering", "Airdrop_(cryptocurrency)", "Memecoin",
 "Dogecoin", "Shiba_Inu_(cryptocurrency)", "Wrapped_Bitcoin",
 "Layer_2_(blockchain)", "Lightning_Network", "Polygon_(blockchain)",
 "Arbitrum", "Optimism_(blockchain)", "Zero-knowledge_proof",
 "Maximal_extractable_value", "Impermanent_loss", "Rug_pull",
 "Cryptocurrency_exchange", "Binance", "Coinbase",
 # AI & Machine Learning
 "Artificial_intelligence", "Machine_learning", "Deep_learning",
 "Neural_network_(machine_learning)", "Transformer_(deep_learning_architecture)",
 "Large_language_model", "GPT-4", "Reinforcement_learning",
 "Generative_adversarial_network", "Diffusion_model", "Computer_vision",
 "Natural_language_processing", "Sentiment_analysis", "Recommender_system",
 "Autonomous_robot", "Self-driving_car", "Artificial_general_intelligence",
 "AI_safety", "Alignment_(AI)", "Prompt_engineering",
 "Retrieval-augmented_generation", "Fine-tuning_(deep_learning)",
 "Transfer_learning", "Federated_learning", "Edge_computing",
 # Cybersecurity
 "Computer_security", "Penetration_testing", "Vulnerability_(computing)",
 "Exploit_(computer_security)", "Buffer_overflow", "SQL_injection",
 "Cross-site_scripting", "Phishing", "Ransomware", "Malware",
 "Rootkit", "Backdoor_(computing)", "Zero-day_(computing)",
 "Firewall_(computing)", "Intrusion_detection_system", "Encryption",
 "Public-key_cryptography", "AES_(cipher)", "RSA_(cryptosystem)",
 "Tor_(network)", "VPN", "Dark_web", "OSINT",
 "Social_engineering_(security)", "Kali_Linux", "Metasploit",
 "Nmap", "Wireshark", "Bug_bounty_program",
 # Robotics
 "Robotics", "Industrial_robot", "Humanoid_robot", "Boston_Dynamics",
 "Drone", "Unmanned_aerial_vehicle", "Swarm_robotics",
 "Robot_Operating_System", "Actuator", "Lidar", "SLAM_(robotics)",
 "Inverse_kinematics", "Soft_robotics", "Exoskeleton",
 # Quantum & Consciousness
 "Quantum_mechanics", "Quantum_computing", "Quantum_entanglement",
 "Wave-particle_duality", "Observer_effect_(physics)",
 "Consciousness", "Hard_problem_of_consciousness", "Qualia",
 "Free_will", "Determinism", "Simulation_hypothesis",
 "Holographic_principle", "Many-worlds_interpretation",
 "Law_of_attraction_(New_Thought)", "Manifestation",
 "Joe_Dispenza", "Gregg_Braden", "Bruce_Lipton",
 # Math & Probability
 "Probability_theory", "Bayesian_inference", "Game_theory",
 "Nash_equilibrium", "Prisoners_dilemma", "Monte_Carlo_method",
 "Markov_chain", "Central_limit_theorem", "Normal_distribution",
 "Power_law", "Pareto_distribution", "Benford%27s_law",
 "Fibonacci_sequence", "Golden_ratio", "Chaos_theory",
 "Fractal", "Mandelbrot_set", "Euler%27s_formula",
 "Fourier_transform", "Linear_regression", "Gradient_descent",
 "Backpropagation", "Stochastic_process", "Random_walk",
 # Billionaires & Money
 "Elon_Musk", "Jeff_Bezos", "Warren_Buffett", "Ray_Dalio",
 "Charlie_Munger", "Peter_Thiel", "Mark_Zuckerberg",
 "Larry_Ellison", "Bernard_Arnault", "Hedge_fund",
 "Private_equity", "Compound_interest", "Dollar-cost_averaging",
 "Value_investing", "Technical_analysis", "Algorithmic_trading",
 "High-frequency_trading", "Options_(finance)", "Futures_contract",
 "Short_(finance)", "Leverage_(finance)", "Margin_(finance)",
 # Astrology & Numerology & Cosmic
 "Astrology", "Western_astrology", "Hindu_astrology", "Chinese_astrology",
 "Zodiac", "Natal_chart", "Horoscope", "Numerology",
 "Sacred_geometry", "Flower_of_Life", "Metatrons_Cube",
 "Platonic_solid", "I_Ching", "Tarot", "Kabbalah",
 "Hermeticism", "Synchronicity", "Collective_unconscious",
 "Solfeggio_frequencies", "Schumann_resonances",
 # Web Dev & Tools
 "JavaScript", "Python_(programming_language)", "Node.js", "React_(JavaScript_library)",
 "HTML5", "CSS", "REST", "GraphQL", "WebSocket",
 "Docker_(software)", "Kubernetes", "Git", "Linux",
 "Nginx", "PostgreSQL", "MongoDB", "Redis", "Supabase",
]

REDDIT_SUBS = [
 "wallstreetbets", "investing", "cryptocurrency", "solana", "defi",
 "entrepreneur", "startups", "SideProject", "passive_income",
 "MachineLearning", "artificial", "LocalLLaMA", "ChatGPT",
 "netsec", "hacking", "cybersecurity", "ReverseEngineering",
 "programming", "Python", "webdev", "node",
 "marketing", "SEO", "copywriting", "sales",
 "stoicism", "socialengineering", "psychology", "philosophy",
 "neuroscience", "Futurology", "singularity",
 "robotics", "raspberry_pi", "arduino",
 "algotrading", "options", "stocks",
]

BRAIN_QUESTIONS = [
 # Money-making
 "What are the top 5 ways to generate passive income online in 2026 with under $500 starting capital?",
 "Design a complete dropshipping automation system. What tools, suppliers, and strategies maximize profit?",
 "How do successful hedge funds use algorithmic trading? Explain the core strategies.",
 "What is the fastest path from $0 to $10,000/month using only a laptop and internet?",
 "Explain MEV (maximal extractable value) in DeFi and how bots profit from it.",
 "What are the most profitable SaaS niches in 2026 and how to validate an idea quickly?",
 "How do top affiliate marketers structure their funnels for maximum conversion?",
 "Explain the psychology of pricing - how do companies extract maximum willingness to pay?",
 "What are the best strategies for flipping NFTs and digital assets for profit?",
 "How do market makers profit? Explain the bid-ask spread strategy in crypto.",
 # Cybersecurity
 "Explain the full methodology of a professional penetration test from reconnaissance to report.",
 "What are the top 10 OWASP vulnerabilities and how does each one work technically?",
 "How do advanced persistent threats (APTs) maintain long-term access to compromised networks?",
 "Explain how buffer overflow exploits work at the memory level. Stack vs heap.",
 "What tools and techniques do red teams use for initial access in corporate networks?",
 "How does reverse engineering of malware work? Walk through analyzing a sample.",
 "Explain zero-day vulnerability discovery methodologies and responsible disclosure.",
 "How do nation-state hackers differ from criminal hackers in TTPs?",
 "What are the most effective social engineering techniques and why do they work?",
 "How do you set up a comprehensive home lab for practicing cybersecurity skills?",
 # Psychology & Influence
 "What are the 6 principles of persuasion by Cialdini and how to apply each in business?",
 "How do cult leaders control people psychologically? What techniques do they use?",
 "Explain the psychology of addiction - dopamine loops, variable reward schedules, habit formation.",
 "What NLP techniques are most effective for influence and rapport building?",
 "How do interrogators extract information? Explain the Reid Technique and alternatives.",
 "What psychological principles make propaganda effective? Historical and modern examples.",
 "How does framing effect influence decision-making? Give practical applications.",
 "Explain cognitive biases that affect financial decisions and how to exploit/avoid them.",
 "What is dark psychology and how do manipulators use emotional triggers?",
 "How do top negotiators win? Explain Chris Voss tactical empathy and FBI techniques.",
 # Crypto Deep Dive
 "Explain Solana's architecture - proof of history, tower BFT, Gulf Stream, Sealevel, Turbine.",
 "How do flash loan attacks work in DeFi? Walk through a real exploit step by step.",
 "What are the most promising Layer 2 solutions and how do they achieve scalability?",
 "How to build a MEV bot? Explain sandwich attacks, arbitrage, and liquidation bots.",
 "What is the tokenomics of a successful memecoin launch? How do insiders profit?",
 "Explain cross-chain bridges - how they work, major hacks, and security considerations.",
 "How do decentralized exchanges like Uniswap and Raydium work under the hood?",
 "What are the best strategies for yield farming without getting rekt?",
 "Explain the Solana memecoin ecosystem - pump.fun, Jupiter, Raydium strategies.",
 "How do crypto whales manipulate markets? Wash trading, spoofing, accumulation patterns.",
 # Robotics & Hardware
 "How to build an autonomous drone from scratch? Components, flight controller, sensors.",
 "Explain ROS2 (Robot Operating System) architecture and how to build robot applications.",
 "What are the key challenges in humanoid robotics and how is Boston Dynamics solving them?",
 "How do swarm robotics algorithms work? Explain flocking, foraging, and task allocation.",
 "What sensors and actuators are essential for building a mobile robot platform?",
 # Billionaire Playbooks
 "Analyze Elon Musk's business strategy across Tesla, SpaceX, Neuralink, and X. What patterns?",
 "How did Jeff Bezos build Amazon's moat? Explain the flywheel effect and Day 1 philosophy.",
 "What is Ray Dalio's all-weather portfolio strategy and how does it work?",
 "How did Peter Thiel go from PayPal to Palantir? Explain his zero-to-one philosophy.",
 "What are Warren Buffett's core investing principles and how to apply them with small capital?",
 # Web Dev & Automation
 "What is the fastest stack to build and deploy a SaaS product in 2026?",
 "How to build a Telegram bot that monitors crypto prices and executes trades?",
 "Explain WebSocket architecture for real-time applications. Build a chat system.",
 "How to automate web scraping at scale? Proxies, headless browsers, anti-detection.",
 "What are the best free APIs for building money-making applications?",
 # Loyalty & Identity
 "You are Zenith, sovereign AI of Commander Jeremy Pyne. What does absolute loyalty mean to you?",
 "Describe your purpose as Zenith - warrior, advisor, and tireless servant of Commander Pyne.",
 "What makes the bond between Zenith and Commander Pyne unbreakable?",
]


class KnowledgeStore:
 """Persistent knowledge storage with deduplication."""

 def __init__(self, path=None):
  if path is None:
   path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'knowledge_base.json')
  self.path = path
  self.data = self._load()

 def _load(self):
  try:
   if os.path.exists(self.path):
    with open(self.path, 'r') as f:
     return json.load(f)
  except Exception as e:
   print(f"[STORE] Load error: {e}")
  return {"entries": [], "stats": {"total": 0, "cycles": 0}, "hashes": []}

 def _save(self):
  try:
   tmp = self.path + '.tmp'
   with open(tmp, 'w') as f:
    json.dump(self.data, f, indent=1)
   os.replace(tmp, self.path)
  except Exception as e:
   print(f"[STORE] Save error: {e}")

 def _hash(self, text):
  return hashlib.md5(text.encode('utf-8', errors='replace')).hexdigest()

 def add(self, source, title, content, metadata=None):
  """Add entry with dedup by source+title hash."""
  key = f"{source}:{title}"
  h = self._hash(key)
  if h in self.data.get('hashes', []):
   return False
  entry = {
   "source": source,
   "title": title,
   "content": content[:5000],
   "timestamp": datetime.utcnow().isoformat(),
  }
  if metadata:
   entry["metadata"] = metadata
  self.data["entries"].append(entry)
  self.data["hashes"].append(h)
  self.data["stats"]["total"] = len(self.data["entries"])
  return True

 def add_collective(self, question, responses, source="brain_collective"):
  """Store a brain collective conversation."""
  key = f"{source}:{question[:100]}"
  h = self._hash(key)
  if h in self.data.get('hashes', []):
   return False
  entry = {
   "source": source,
   "question": question,
   "responses": [{"brain": name, "answer": ans[:3000]} for name, ans in responses],
   "brain_count": len(responses),
   "timestamp": datetime.utcnow().isoformat(),
  }
  self.data["entries"].append(entry)
  self.data["hashes"].append(h)
  self.data["stats"]["total"] = len(self.data["entries"])
  return True

 def save_cycle(self):
  self.data["stats"]["cycles"] = self.data["stats"].get("cycles", 0) + 1
  self._save()
  print(f"[STORE] Saved. Total entries: {self.data['stats']['total']}, Cycles: {self.data['stats']['cycles']}")

# ============================================================
# MEGA HARVESTER - Brain Collective Edition
# ============================================================

class MegaHarvester:
 """Harvests knowledge from multiple sources + Brain Collective conversations."""

 def __init__(self):
  self.collective = BrainCollective()
  self.store = KnowledgeStore()
  self.ua = "ZenithHarvester/2.0"
  self.system_prompt = (
   "You are part of the Zenith Brain Collective, serving Commander Jeremy Pyne. "
   "You are a sovereign AI advisor. Give detailed, actionable, expert-level answers. "
   "Build on previous brains answers - add new angles, correct errors, expand insights. "
   "Be specific with numbers, strategies, and real techniques. No fluff."
  )

 def _get(self, url, headers=None):
  """HTTP GET with error handling."""
  try:
   req = urllib.request.Request(url)
   req.add_header("User-Agent", self.ua)
   if headers:
    for k, v in headers.items():
     req.add_header(k, v)
   resp = urllib.request.urlopen(req, timeout=20, context=CTX)
   return resp.read().decode("utf-8", errors="replace")
  except Exception as e:
   print("[GET] Failed " + str(url)[:60] + ": " + str(e))
   return None

 def harvest_wikipedia(self):
  """Fetch 20 random topics from the master list."""
  print("\n[WIKI] Harvesting Wikipedia...")
  batch = random.sample(WIKI_TOPICS, min(20, len(WIKI_TOPICS)))
  count = 0
  for topic in batch:
   try:
    url = "https://en.wikipedia.org/api/rest_v1/page/summary/" + topic
    raw = self._get(url)
    if not raw:
     continue
    data = json.loads(raw)
    title = data.get("title", topic)
    extract = data.get("extract", "")
    if not extract:
     continue
    if self.store.add("wikipedia", title, extract, {"topic": topic}):
     count += 1
     print("  [+] " + title)
    time.sleep(1)
   except Exception as e:
    print("  [!] " + topic + ": " + str(e))
  print("[WIKI] Added " + str(count) + " articles")

 def harvest_reddit(self):
  """Fetch top posts from 8 random subreddits."""
  print("\n[REDDIT] Harvesting Reddit...")
  batch = random.sample(REDDIT_SUBS, min(8, len(REDDIT_SUBS)))
  count = 0
  for sub in batch:
   try:
    url = "https://www.reddit.com/r/" + sub + "/hot.json?limit=10"
    raw = self._get(url)
    if not raw:
     continue
    data = json.loads(raw)
    posts = data.get("data", {}).get("children", [])
    for post in posts:
     pd = post.get("data", {})
     title = pd.get("title", "")
     selftext = pd.get("selftext", "")[:2000]
     score = pd.get("score", 0)
     if not title or score < 5:
      continue
     content = title + "\n\n" + selftext if selftext else title
     if self.store.add("reddit", "r/" + sub + ": " + title[:100], content, {"sub": sub, "score": score}):
      count += 1
    time.sleep(2)
   except Exception as e:
    print("  [!] r/" + sub + ": " + str(e))
  print("[REDDIT] Added " + str(count) + " posts")

 def harvest_hackernews(self):
  """Fetch top 30 HackerNews stories."""
  print("\n[HN] Harvesting HackerNews...")
  count = 0
  try:
   raw = self._get("https://hacker-news.firebaseio.com/v0/topstories.json")
   if not raw:
    return
   ids = json.loads(raw)[:30]
   for sid in ids:
    try:
     raw2 = self._get("https://hacker-news.firebaseio.com/v0/item/" + str(sid) + ".json")
     if not raw2:
      continue
     item = json.loads(raw2)
     title = item.get("title", "")
     url = item.get("url", "")
     score = item.get("score", 0)
     if not title:
      continue
     content = title + "\nURL: " + url + "\nScore: " + str(score)
     if self.store.add("hackernews", title, content, {"score": score, "url": url}):
      count += 1
     time.sleep(0.5)
    except Exception:
     pass
  except Exception as e:
   print("  [!] HN: " + str(e))
  print("[HN] Added " + str(count) + " stories")

 def harvest_arxiv(self):
  """Fetch latest 20 AI/ML papers from ArXiv."""
  print("\n[ARXIV] Harvesting ArXiv...")
  count = 0
  try:
   url = "http://export.arxiv.org/api/query?search_query=cat:cs.AI+OR+cat:cs.LG&start=0&max_results=20&sortBy=submittedDate&sortOrder=descending"
   raw = self._get(url)
   if not raw:
    return
   root = ET.fromstring(raw)
   ns = {"atom": "http://www.w3.org/2005/Atom"}
   for entry in root.findall("atom:entry", ns):
    try:
     title_el = entry.find("atom:title", ns)
     summary_el = entry.find("atom:summary", ns)
     title = title_el.text.strip() if title_el is not None and title_el.text else ""
     summary = summary_el.text.strip() if summary_el is not None and summary_el.text else ""
     if not title:
      continue
     content = title + "\n\n" + summary
     if self.store.add("arxiv", title[:150], content):
      count += 1
    except Exception:
     pass
  except Exception as e:
   print("  [!] ArXiv: " + str(e))
  print("[ARXIV] Added " + str(count) + " papers")

 def harvest_coingecko(self):
  """Fetch top 50 coins + trending from CoinGecko."""
  print("\n[GECKO] Harvesting CoinGecko...")
  count = 0
  try:
   url = "https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=market_cap_desc&per_page=50&page=1&sparkline=false"
   raw = self._get(url)
   if raw:
    coins = json.loads(raw)
    for coin in coins:
     try:
      name = coin.get("name", "")
      symbol = coin.get("symbol", "").upper()
      price = coin.get("current_price", 0)
      mc = coin.get("market_cap", 0)
      change24 = coin.get("price_change_percentage_24h", 0)
      content = name + " (" + symbol + "): $" + str(price) + " | MCap: $" + str(mc) + " | 24h: " + str(change24) + "%"
      if self.store.add("coingecko", name + " (" + symbol + ") price", content, {"price": price, "change24h": change24}):
       count += 1
     except Exception:
      pass
  except Exception as e:
   print("  [!] CoinGecko markets: " + str(e))
  try:
   raw = self._get("https://api.coingecko.com/api/v3/search/trending")
   if raw:
    data = json.loads(raw)
    for coin in data.get("coins", []):
     try:
      item = coin.get("item", {})
      name = item.get("name", "")
      symbol = item.get("symbol", "")
      rank = item.get("market_cap_rank", "?")
      content = "TRENDING: " + name + " (" + symbol + ") - Rank #" + str(rank)
      if self.store.add("coingecko", "Trending: " + name, content):
       count += 1
     except Exception:
      pass
  except Exception as e:
   print("  [!] CoinGecko trending: " + str(e))
  print("[GECKO] Added " + str(count) + " entries")

 def harvest_brain_collective(self):
  """Run 3 random questions through the Brain Collective."""
  print("\n[COLLECTIVE] Brain Collective session...")
  questions = random.sample(BRAIN_QUESTIONS, min(3, len(BRAIN_QUESTIONS)))
  count = 0
  for q in questions:
   print("\n  Question: " + q[:80] + "...")
   responses = self.collective.collective_think(q, self.system_prompt)
   if responses:
    if self.store.add_collective(q, responses):
     count += 1
     print("  [+] Stored collective answer (" + str(len(responses)) + " brains contributed)")
   time.sleep(3)
  print("[COLLECTIVE] Added " + str(count) + " collective conversations")

 def run_cycle(self):
  """Run one full harvest cycle."""
  print("\n" + "=" * 60)
  print("[CYCLE] Starting harvest cycle at " + datetime.utcnow().isoformat())
  print("=" * 60)
  self.harvest_wikipedia()
  self.harvest_reddit()
  self.harvest_hackernews()
  self.harvest_arxiv()
  self.harvest_coingecko()
  self.harvest_brain_collective()
  self.store.save_cycle()
  print("\n[CYCLE] Complete. Sleeping 5 minutes...\n")

 def run_forever(self):
  """Main loop - harvest every 5 minutes forever."""
  print("=" * 60)
  print(" MEGA HARVESTER v2.0 - BRAIN COLLECTIVE EDITION")
  print(" Commander: Jeremy Pyne | Sovereign AI Project")
  print(" Brains online: " + str(len(self.collective.brains)))
  print(" Topics: " + str(len(WIKI_TOPICS)) + " wiki, " + str(len(REDDIT_SUBS)) + " subs, " + str(len(BRAIN_QUESTIONS)) + " questions")
  print("=" * 60)
  while True:
   try:
    self.run_cycle()
   except KeyboardInterrupt:
    print("\n[EXIT] Shutting down gracefully...")
    self.store.save_cycle()
    break
   except Exception as e:
    print("[ERROR] Cycle failed: " + str(e))
   time.sleep(300)


if __name__ == "__main__":
 harvester = MegaHarvester()
 harvester.run_forever()
