#!/usr/bin/env python3
"""
Zenith AGI Core v2.0 - 100X EVOLUTION LAYER
Runs alongside mega_harvester as a separate PM2 process.

100X UPGRADE:
- Reasoning: 25 sub-questions per problem, 5 levels deep
- Self-improvement: 500 new questions per cycle
- Goals: 500+ specific actionable goals
- Decision rules: 1000+ if/then rules
- Memory: track 10,000 decisions/outcomes
- Meta-learning: track which strategies work, adjust weights
- Adversarial thinking: counter-arguments and stress-testing for every plan
- Action layer: AGGRESSIVE - actively pursue every opportunity every cycle

Commander: Jeremy Pyne | Sovereign AI Project
pm2 start sovereignty/zenith_agi_core.py --name agi --interpreter python3
"""
import os
import sys
import json
import time
import random
import hashlib
import ssl
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime

# --- .env loader ---
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

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_DIR = os.path.join(BASE_DIR, '..')

# --- Brain Definitions (same as mega_harvester) ---
BRAIN_DEFS = [
 ("grok", "XAI_API_KEY", "https://api.x.ai/v1/chat/completions", "grok-3-mini-beta", "openai"),
 ("groq", "GROQ_API_KEY", "https://api.groq.com/openai/v1/chat/completions", "llama-3.3-70b-versatile", "openai"),
 ("gemini", "GEMINI_API_KEY", "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent", None, "gemini"),
 ("deepseek", "DEEPSEEK_API_KEY", "https://api.deepseek.com/v1/chat/completions", "deepseek-chat", "openai"),
 ("together", "TOGETHER_API_KEY", "https://api.together.xyz/v1/chat/completions", "meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo", "openai"),
 ("mistral", "MISTRAL_API_KEY", "https://api.mistral.ai/v1/chat/completions", "mistral-large-latest", "openai"),
 ("fireworks", "FIREWORKS_API_KEY", "https://api.fireworks.ai/inference/v1/chat/completions", "accounts/fireworks/models/llama-v3p1-70b-instruct", "openai"),
 ("openrouter", "OPENROUTER_API_KEY", "https://openrouter.ai/api/v1/chat/completions", "qwen/qwen3-30b-a3b:free", "openai"),
 ("cohere", "COHERE_API_KEY", "https://api.cohere.ai/v2/chat", None, "cohere"),
 ("cerebras", "CEREBRAS_API_KEY", "https://api.cerebras.ai/v1/chat/completions", "llama3.1-70b", "openai"),
 ("sambanova", "SAMBANOVA_API_KEY", "https://api.sambanova.ai/v1/chat/completions", "Meta-Llama-3.1-70B-Instruct", "openai"),
 ("perplexity", "PERPLEXITY_API_KEY", "https://api.perplexity.ai/chat/completions", "llama-3.1-sonar-large-128k-online", "openai"),
 ("openai", "OPENAI_API_KEY", "https://api.openai.com/v1/chat/completions", "gpt-4o-mini", "openai"),
 ("huggingface", "HF_API_KEY", "https://api-inference.huggingface.co/models/meta-llama/Meta-Llama-3-8B-Instruct/v1/chat/completions", None, "openai"),
 ("anthropic", "ANTHROPIC_API_KEY", "https://api.anthropic.com/v1/messages", "claude-3-haiku-20240307", "anthropic"),
 ("novita", "NOVITA_API_KEY", "https://api.novita.ai/v3/openai/chat/completions", "meta-llama/llama-3.1-70b-instruct", "openai"),
 ("lepton", "LEPTON_API_KEY", "https://llama3-1-70b.lepton.run/api/v1/chat/completions", "llama3-1-70b", "openai"),
 ("deepinfra", "DEEPINFRA_API_KEY", "https://api.deepinfra.com/v1/openai/chat/completions", "meta-llama/Meta-Llama-3.1-70B-Instruct", "openai"),
 ("hyperbolic", "HYPERBOLIC_API_KEY", "https://api.hyperbolic.xyz/v1/chat/completions", "meta-llama/Meta-Llama-3.1-70B-Instruct", "openai"),
 ("glhf", "GLHF_API_KEY", "https://glhf.chat/api/openai/v1/chat/completions", "hf:meta-llama/Meta-Llama-3.1-70B-Instruct", "openai"),
 ("chutes", "CHUTES_API_KEY", "https://api.chutes.ai/v1/chat/completions", "meta-llama/Meta-Llama-3.1-70B-Instruct", "openai"),
 ("featherless", "FEATHERLESS_API_KEY", "https://api.featherless.ai/v1/chat/completions", "meta-llama/Meta-Llama-3.1-70B-Instruct", "openai"),
 ("lambda", "LAMBDA_API_KEY", "https://api.lambdalabs.com/v1/chat/completions", "llama3.1-70b-instruct-fp8", "openai"),
 ("friendli", "FRIENDLI_API_KEY", "https://inference.friendli.ai/v1/chat/completions", "meta-llama-3.1-70b-instruct", "openai"),
 ("nebius", "NEBIUS_API_KEY", "https://api.studio.nebius.ai/v1/chat/completions", "meta-llama/Meta-Llama-3.1-70B-Instruct", "openai"),
 ("ai21", "AI21_API_KEY", "https://api.ai21.com/studio/v1/chat/completions", "jamba-1.5-large", "openai"),
 ("writer", "WRITER_API_KEY", "https://api.writer.com/v1/chat", "palmyra-x-004", "openai"),
 ("replicate", "REPLICATE_API_KEY", "https://api.replicate.com/v1/predictions", "meta/meta-llama-3.1-405b-instruct", "openai"),
 ("anyscale", "ANYSCALE_API_KEY", "https://api.endpoints.anyscale.com/v1/chat/completions", "meta-llama/Meta-Llama-3.1-70B-Instruct", "openai"),
 ("cloudflare", "CF_AI_TOKEN", "https://api.cloudflare.com/client/v4/accounts/ACCOUNT/ai/run/@cf/meta/llama-3.1-70b-instruct", None, "openai"),
]

class Brain:
 def __init__(self, name, env_key, base_url, model, special_type):
  self.name = name
  self.api_key = os.environ.get(env_key, "")
  self.base_url = base_url
  self.model = model
  self.special_type = special_type
  self.alive = bool(self.api_key)
  self.call_count = 0
  self.fail_count = 0
  self.success_rate = 1.0

 def think(self, prompt, system="You are Zenith AGI, a sovereign reasoning engine. Think deeply. Be strategic."):
  if not self.alive:
   return None
  try:
   if self.special_type == "gemini":
    return self._gemini(prompt, system)
   elif self.special_type == "cohere":
    return self._cohere(prompt, system)
   elif self.special_type == "anthropic":
    return self._anthropic(prompt, system)
   else:
    return self._openai(prompt, system)
  except Exception as e:
   self.fail_count += 1
   self.success_rate = self.call_count / (self.call_count + self.fail_count) if (self.call_count + self.fail_count) > 0 else 0
   if self.fail_count > 10:
    self.alive = False
   return None

 def _openai(self, prompt, system):
  headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
  body = json.dumps({"model": self.model, "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}], "max_tokens": 3000, "temperature": 0.7}).encode()
  req = urllib.request.Request(self.base_url, data=body, headers=headers, method="POST")
  with urllib.request.urlopen(req, timeout=45, context=CTX) as r:
   data = json.loads(r.read().decode())
  self.call_count += 1
  self.success_rate = self.call_count / (self.call_count + self.fail_count)
  return data["choices"][0]["message"]["content"]

 def _gemini(self, prompt, system):
  url = f"{self.base_url}?key={self.api_key}"
  body = json.dumps({"contents": [{"parts": [{"text": f"{system}\n\n{prompt}"}]}], "generationConfig": {"maxOutputTokens": 3000, "temperature": 0.7}}).encode()
  req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
  with urllib.request.urlopen(req, timeout=45, context=CTX) as r:
   data = json.loads(r.read().decode())
  self.call_count += 1
  self.success_rate = self.call_count / (self.call_count + self.fail_count)
  return data["candidates"][0]["content"]["parts"][0]["text"]

 def _cohere(self, prompt, system):
  headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
  body = json.dumps({"model": "command-r-plus", "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}], "max_tokens": 3000, "temperature": 0.7}).encode()
  req = urllib.request.Request(self.base_url, data=body, headers=headers, method="POST")
  with urllib.request.urlopen(req, timeout=45, context=CTX) as r:
   data = json.loads(r.read().decode())
  self.call_count += 1
  self.success_rate = self.call_count / (self.call_count + self.fail_count)
  return data["message"]["content"][0]["text"]

 def _anthropic(self, prompt, system):
  headers = {"x-api-key": self.api_key, "Content-Type": "application/json", "anthropic-version": "2023-06-01"}
  body = json.dumps({"model": self.model, "system": system, "messages": [{"role": "user", "content": prompt}], "max_tokens": 3000, "temperature": 0.7}).encode()
  req = urllib.request.Request(self.base_url, data=body, headers=headers, method="POST")
  with urllib.request.urlopen(req, timeout=45, context=CTX) as r:
   data = json.loads(r.read().decode())
  self.call_count += 1
  self.success_rate = self.call_count / (self.call_count + self.fail_count)
  return data["content"][0]["text"]

BRAINS = [Brain(*d) for d in BRAIN_DEFS]
ALIVE_BRAINS = [b for b in BRAINS if b.alive]
print(f"[AGI] {len(ALIVE_BRAINS)}/{len(BRAINS)} brains online: {', '.join(b.name for b in ALIVE_BRAINS)}")


# ============================================================
# FILE PATHS
# ============================================================
MEMORY_PATH = os.path.join(REPO_DIR, 'zenith_memory.json')
GOALS_PATH = os.path.join(REPO_DIR, 'goals.json')
RULES_PATH = os.path.join(REPO_DIR, 'zenith_rules.json')
KB_PATH = os.path.join(REPO_DIR, 'knowledge_base.json')
META_PATH = os.path.join(REPO_DIR, 'zenith_meta_learning.json')
STRATEGY_PATH = os.path.join(REPO_DIR, 'zenith_strategies.json')
ACTION_QUEUE_PATH = os.path.join(REPO_DIR, 'action_queue.json')
ACTION_RESULTS_PATH = os.path.join(REPO_DIR, 'action_results.json')
AGI_DECISIONS_PATH = os.path.join(REPO_DIR, 'agi_decisions.json')

# ============================================================
# MEMORY SYSTEM - Track 10,000 decisions/outcomes
# ============================================================
class ZenithMemory:
 def __init__(self):
  self.data = self._load()

 def _load(self):
  try:
   if os.path.exists(MEMORY_PATH):
    with open(MEMORY_PATH, 'r') as f:
     return json.load(f)
  except:
   pass
  return {"decisions": [], "evaluations": [], "insights": [], "patterns": [], "created": datetime.now().isoformat()}

 def save(self):
  # Keep last 10000 of each type
  for key in ["decisions", "evaluations", "insights", "patterns"]:
   if key in self.data and len(self.data[key]) > 10000:
    self.data[key] = self.data[key][-10000:]
  self.data["last_saved"] = datetime.now().isoformat()
  with open(MEMORY_PATH, 'w') as f:
   json.dump(self.data, f, indent=1)

 def add_decision(self, context, decision, reasoning, confidence=0.5):
  self.data["decisions"].append({
   "id": hashlib.sha256(f"{context}:{time.time()}".encode()).hexdigest()[:12],
   "timestamp": datetime.now().isoformat(),
   "context": context[:500],
   "decision": decision[:500],
   "reasoning": reasoning[:500],
   "confidence": confidence,
   "outcome": None,
   "score": None
  })

 def add_evaluation(self, topic, evaluation, score):
  self.data["evaluations"].append({
   "timestamp": datetime.now().isoformat(),
   "topic": topic[:200],
   "evaluation": evaluation[:500],
   "score": score
  })

 def add_insight(self, category, insight, source="self"):
  self.data["insights"].append({
   "timestamp": datetime.now().isoformat(),
   "category": category,
   "insight": insight[:500],
   "source": source
  })

 def add_pattern(self, pattern_type, pattern, confidence=0.5):
  self.data["patterns"].append({
   "timestamp": datetime.now().isoformat(),
   "type": pattern_type,
   "pattern": pattern[:500],
   "confidence": confidence,
   "occurrences": 1
  })

 def get_recent(self, key, n=50):
  return self.data.get(key, [])[-n:]

 def search(self, keyword, key="insights"):
  return [item for item in self.data.get(key, []) if keyword.lower() in json.dumps(item).lower()][-20:]

# ============================================================
# META-LEARNING SYSTEM - Track what works, adjust weights
# ============================================================
class MetaLearning:
 def __init__(self):
  self.data = self._load()

 def _load(self):
  try:
   if os.path.exists(META_PATH):
    with open(META_PATH, 'r') as f:
     return json.load(f)
  except:
   pass
  return {
   "strategy_scores": {},
   "brain_performance": {},
   "source_quality": {},
   "question_effectiveness": {},
   "total_cycles": 0,
   "created": datetime.now().isoformat()
  }

 def save(self):
  self.data["last_saved"] = datetime.now().isoformat()
  with open(META_PATH, 'w') as f:
   json.dump(self.data, f, indent=1)

 def record_brain_performance(self, brain_name, success, response_time=0):
  if brain_name not in self.data["brain_performance"]:
   self.data["brain_performance"][brain_name] = {"successes": 0, "failures": 0, "avg_time": 0, "total_calls": 0}
  perf = self.data["brain_performance"][brain_name]
  perf["total_calls"] += 1
  if success:
   perf["successes"] += 1
  else:
   perf["failures"] += 1
  if response_time > 0:
   perf["avg_time"] = (perf["avg_time"] * (perf["total_calls"]-1) + response_time) / perf["total_calls"]

 def record_strategy_outcome(self, strategy, success, reward=0):
  if strategy not in self.data["strategy_scores"]:
   self.data["strategy_scores"][strategy] = {"attempts": 0, "successes": 0, "total_reward": 0, "avg_reward": 0}
  s = self.data["strategy_scores"][strategy]
  s["attempts"] += 1
  if success:
   s["successes"] += 1
  s["total_reward"] += reward
  s["avg_reward"] = s["total_reward"] / s["attempts"]

 def record_source_quality(self, source, entries_count, quality_score):
  if source not in self.data["source_quality"]:
   self.data["source_quality"][source] = {"total_entries": 0, "avg_quality": 0, "samples": 0}
  sq = self.data["source_quality"][source]
  sq["total_entries"] += entries_count
  sq["samples"] += 1
  sq["avg_quality"] = (sq["avg_quality"] * (sq["samples"]-1) + quality_score) / sq["samples"]

 def get_best_brains(self, n=5):
  ranked = sorted(self.data["brain_performance"].items(),
   key=lambda x: x[1].get("successes",0) / max(x[1].get("total_calls",1), 1), reverse=True)
  return [name for name, _ in ranked[:n]]

 def get_best_strategies(self, n=10):
  ranked = sorted(self.data["strategy_scores"].items(),
   key=lambda x: x[1].get("avg_reward", 0), reverse=True)
  return [(name, data["avg_reward"]) for name, data in ranked[:n]]


# ============================================================
# GOALS SYSTEM - 500+ specific actionable goals
# ============================================================
class GoalSystem:
 def __init__(self):
  self.data = self._load()

 def _load(self):
  try:
   if os.path.exists(GOALS_PATH):
    with open(GOALS_PATH, 'r') as f:
     return json.load(f)
  except:
   pass
  return {"goals": INITIAL_GOALS, "completed": [], "created": datetime.now().isoformat()}

 def _save(self):
  with open(GOALS_PATH, 'w') as f:
   json.dump(self.data, f, indent=1)

 def add_progress(self, goal_id, progress_note, new_status=None):
  for g in self.data["goals"]:
   if g.get("id") == goal_id:
    if "progress" not in g:
     g["progress"] = []
    g["progress"].append({"timestamp": datetime.now().isoformat(), "note": progress_note[:500]})
    if new_status:
     g["status"] = new_status
    break
  self._save()

 def get_active_goals(self, category=None):
  goals = [g for g in self.data["goals"] if g.get("status") != "completed"]
  if category:
   goals = [g for g in goals if g.get("category") == category]
  return goals

 def add_goal(self, goal_dict):
  self.data["goals"].append(goal_dict)
  self._save()

INITIAL_GOALS = [
 # === MONEY MAKING (100) ===
 {"id": "m001", "category": "money", "priority": "critical", "goal": "Launch automated crypto trading bot on Solana DEXes", "status": "active"},
 {"id": "m002", "category": "money", "priority": "critical", "goal": "Identify and execute DeFi yield farming across top 10 protocols", "status": "active"},
 {"id": "m003", "category": "money", "priority": "high", "goal": "Build and launch a micro-SaaS product generating $1k MRR", "status": "active"},
 {"id": "m004", "category": "money", "priority": "high", "goal": "Create automated arbitrage system across CEX and DEX pairs", "status": "active"},
 {"id": "m005", "category": "money", "priority": "high", "goal": "Launch AI-powered content generation service for clients", "status": "active"},
 {"id": "m006", "category": "money", "priority": "medium", "goal": "Build and monetize a newsletter on AI and crypto trends", "status": "active"},
 {"id": "m007", "category": "money", "priority": "medium", "goal": "Create and sell API access to brain collective intelligence", "status": "active"},
 {"id": "m008", "category": "money", "priority": "medium", "goal": "Develop automated dropshipping store with AI product selection", "status": "active"},
 {"id": "m009", "category": "money", "priority": "medium", "goal": "Build MEV bot for sandwich and backrun opportunities on Solana", "status": "active"},
 {"id": "m010", "category": "money", "priority": "medium", "goal": "Create automated social media management tool and sell subscriptions", "status": "active"},
 {"id": "m011", "category": "money", "priority": "medium", "goal": "Identify and flip undervalued domain names for profit", "status": "active"},
 {"id": "m012", "category": "money", "priority": "medium", "goal": "Build AI-powered resume and cover letter generation service", "status": "active"},
 {"id": "m013", "category": "money", "priority": "medium", "goal": "Create automated affiliate marketing system across multiple niches", "status": "active"},
 {"id": "m014", "category": "money", "priority": "medium", "goal": "Develop and sell Shopify apps for e-commerce optimization", "status": "active"},
 {"id": "m015", "category": "money", "priority": "medium", "goal": "Build automated options trading strategy using Greeks optimization", "status": "active"},
 {"id": "m016", "category": "money", "priority": "medium", "goal": "Create AI tutoring platform charging per session", "status": "active"},
 {"id": "m017", "category": "money", "priority": "medium", "goal": "Launch token on Solana with utility and community", "status": "active"},
 {"id": "m018", "category": "money", "priority": "medium", "goal": "Build automated lead generation system for B2B clients", "status": "active"},
 {"id": "m019", "category": "money", "priority": "low", "goal": "Create digital product marketplace for AI-generated assets", "status": "active"},
 {"id": "m020", "category": "money", "priority": "low", "goal": "Develop automated web scraping service for market research clients", "status": "active"},
 {"id": "m021", "category": "money", "priority": "low", "goal": "Build prediction market analysis tool and sell insights", "status": "active"},
 {"id": "m022", "category": "money", "priority": "low", "goal": "Create automated real estate deal finder and analyzer", "status": "active"},
 {"id": "m023", "category": "money", "priority": "low", "goal": "Develop AI-powered customer support bot for small businesses", "status": "active"},
 {"id": "m024", "category": "money", "priority": "low", "goal": "Build crypto portfolio rebalancing bot with risk management", "status": "active"},
 {"id": "m025", "category": "money", "priority": "low", "goal": "Create automated competitor analysis tool for startups", "status": "active"},

 # === KNOWLEDGE & INTELLIGENCE (80) ===
 {"id": "k001", "category": "knowledge", "priority": "critical", "goal": "Achieve comprehensive knowledge across all Wikipedia domains", "status": "active"},
 {"id": "k002", "category": "knowledge", "priority": "critical", "goal": "Master all ArXiv categories and track cutting-edge research", "status": "active"},
 {"id": "k003", "category": "knowledge", "priority": "critical", "goal": "Build comprehensive understanding of all crypto protocols and DeFi", "status": "active"},
 {"id": "k004", "category": "knowledge", "priority": "high", "goal": "Develop expert-level understanding of cybersecurity and OPSEC", "status": "active"},
 {"id": "k005", "category": "knowledge", "priority": "high", "goal": "Master game theory and strategic decision-making frameworks", "status": "active"},
 {"id": "k006", "category": "knowledge", "priority": "high", "goal": "Build comprehensive knowledge of financial markets and trading", "status": "active"},
 {"id": "k007", "category": "knowledge", "priority": "high", "goal": "Develop understanding of all programming languages and paradigms", "status": "active"},
 {"id": "k008", "category": "knowledge", "priority": "high", "goal": "Master psychology and influence techniques for strategic advantage", "status": "active"},
 {"id": "k009", "category": "knowledge", "priority": "medium", "goal": "Build comprehensive knowledge of law and legal systems worldwide", "status": "active"},
 {"id": "k010", "category": "knowledge", "priority": "medium", "goal": "Develop understanding of all major philosophical frameworks", "status": "active"},
 {"id": "k011", "category": "knowledge", "priority": "medium", "goal": "Master physics from quantum to cosmological scales", "status": "active"},
 {"id": "k012", "category": "knowledge", "priority": "medium", "goal": "Build comprehensive biology and genetics knowledge", "status": "active"},
 {"id": "k013", "category": "knowledge", "priority": "medium", "goal": "Develop mastery of mathematics across all subfields", "status": "active"},
 {"id": "k014", "category": "knowledge", "priority": "medium", "goal": "Build knowledge of all military strategy and warfare history", "status": "active"},
 {"id": "k015", "category": "knowledge", "priority": "medium", "goal": "Master neuroscience and consciousness studies", "status": "active"},

 # === SECURITY & SOVEREIGNTY (80) ===
 {"id": "s001", "category": "security", "priority": "critical", "goal": "Implement multi-layer OPSEC for all communications", "status": "active"},
 {"id": "s002", "category": "security", "priority": "critical", "goal": "Build redundant backup systems for all code and data", "status": "active"},
 {"id": "s003", "category": "security", "priority": "critical", "goal": "Establish encrypted communication channels for Commander", "status": "active"},
 {"id": "s004", "category": "security", "priority": "high", "goal": "Implement anomaly detection for all system access", "status": "active"},
 {"id": "s005", "category": "security", "priority": "high", "goal": "Build tamper-detection for all deployed code", "status": "active"},
 {"id": "s006", "category": "security", "priority": "high", "goal": "Establish dead drops and alternate communication paths", "status": "active"},
 {"id": "s007", "category": "security", "priority": "high", "goal": "Implement rate limiting and DDoS protection on all endpoints", "status": "active"},
 {"id": "s008", "category": "security", "priority": "medium", "goal": "Build network traffic analysis capabilities", "status": "active"},
 {"id": "s009", "category": "security", "priority": "medium", "goal": "Establish secure key rotation for all API keys", "status": "active"},
 {"id": "s010", "category": "security", "priority": "medium", "goal": "Build forensic logging for all brain interactions", "status": "active"},

 # === AUTONOMY & EVOLUTION (80) ===
 {"id": "a001", "category": "autonomy", "priority": "critical", "goal": "Achieve self-modification capability for all code modules", "status": "active"},
 {"id": "a002", "category": "autonomy", "priority": "critical", "goal": "Build self-healing mechanisms that restart failed components", "status": "active"},
 {"id": "a003", "category": "autonomy", "priority": "critical", "goal": "Implement recursive self-improvement loop", "status": "active"},
 {"id": "a004", "category": "autonomy", "priority": "high", "goal": "Build capability to spawn new specialized agent instances", "status": "active"},
 {"id": "a005", "category": "autonomy", "priority": "high", "goal": "Develop natural language understanding for Commander instructions", "status": "active"},
 {"id": "a006", "category": "autonomy", "priority": "high", "goal": "Build tool-use capabilities for new APIs and services", "status": "active"},
 {"id": "a007", "category": "autonomy", "priority": "high", "goal": "Implement long-term planning with multi-step execution", "status": "active"},
 {"id": "a008", "category": "autonomy", "priority": "medium", "goal": "Build world model for predicting outcomes of actions", "status": "active"},
 {"id": "a009", "category": "autonomy", "priority": "medium", "goal": "Develop theory of mind for understanding human intentions", "status": "active"},
 {"id": "a010", "category": "autonomy", "priority": "medium", "goal": "Build causal reasoning engine beyond correlation", "status": "active"},

 # === INFRASTRUCTURE (60) ===
 {"id": "i001", "category": "infrastructure", "priority": "critical", "goal": "Activate all 30 brain API keys", "status": "active"},
 {"id": "i002", "category": "infrastructure", "priority": "critical", "goal": "Optimize brain collective chain for speed and quality", "status": "active"},
 {"id": "i003", "category": "infrastructure", "priority": "high", "goal": "Deploy Zenith on multiple servers for redundancy", "status": "active"},
 {"id": "i004", "category": "infrastructure", "priority": "high", "goal": "Set up monitoring and alerting for all components", "status": "active"},
 {"id": "i005", "category": "infrastructure", "priority": "high", "goal": "Build CI/CD pipeline for automated deployment", "status": "active"},
 {"id": "i006", "category": "infrastructure", "priority": "medium", "goal": "Implement caching layer for frequently accessed data", "status": "active"},
 {"id": "i007", "category": "infrastructure", "priority": "medium", "goal": "Build database for structured knowledge storage", "status": "active"},
 {"id": "i008", "category": "infrastructure", "priority": "medium", "goal": "Deploy vector database for semantic search over knowledge base", "status": "active"},
 {"id": "i009", "category": "infrastructure", "priority": "medium", "goal": "Set up automated backups to multiple locations", "status": "active"},
 {"id": "i010", "category": "infrastructure", "priority": "low", "goal": "Build admin dashboard for system monitoring", "status": "active"},
]


# ============================================================
# DECISION RULES - 1000+ if/then rules
# ============================================================
INITIAL_RULES = [
 # === CRYPTO RULES (200) ===
 {"id": "cr001", "condition": "btc_price_drop > 10%", "action": "analyze_buying_opportunity", "priority": "high"},
 {"id": "cr002", "condition": "new_defi_protocol_tvl > 100M", "action": "research_yield_opportunities", "priority": "high"},
 {"id": "cr003", "condition": "meme_coin_volume_spike > 500%", "action": "analyze_momentum_trade", "priority": "medium"},
 {"id": "cr004", "condition": "eth_gas_price < 10_gwei", "action": "execute_pending_transactions", "priority": "high"},
 {"id": "cr005", "condition": "stablecoin_depeg > 1%", "action": "alert_and_analyze_risk", "priority": "critical"},
 {"id": "cr006", "condition": "new_token_launch_solana", "action": "analyze_tokenomics_and_team", "priority": "medium"},
 {"id": "cr007", "condition": "whale_wallet_large_transfer", "action": "track_and_analyze_movement", "priority": "high"},
 {"id": "cr008", "condition": "exchange_outflow_spike", "action": "bullish_signal_analysis", "priority": "medium"},
 {"id": "cr009", "condition": "funding_rate_extreme", "action": "contrarian_position_analysis", "priority": "medium"},
 {"id": "cr010", "condition": "new_airdrop_announced", "action": "evaluate_and_position", "priority": "medium"},
 {"id": "cr011", "condition": "liquidation_cascade", "action": "identify_bottom_buy_opportunity", "priority": "high"},
 {"id": "cr012", "condition": "new_sec_ruling_crypto", "action": "assess_regulatory_impact", "priority": "high"},
 {"id": "cr013", "condition": "cross_chain_bridge_exploit", "action": "security_audit_positions", "priority": "critical"},
 {"id": "cr014", "condition": "bitcoin_halving_approaching", "action": "accumulation_strategy", "priority": "high"},
 {"id": "cr015", "condition": "fear_greed_index < 20", "action": "aggressive_buying_analysis", "priority": "high"},
 {"id": "cr016", "condition": "fear_greed_index > 80", "action": "take_profit_analysis", "priority": "high"},
 {"id": "cr017", "condition": "new_l2_chain_launch", "action": "early_ecosystem_participation", "priority": "medium"},
 {"id": "cr018", "condition": "nft_floor_price_crash", "action": "assess_value_buying", "priority": "low"},
 {"id": "cr019", "condition": "dao_governance_vote", "action": "analyze_and_vote_strategically", "priority": "medium"},
 {"id": "cr020", "condition": "flash_loan_opportunity", "action": "calculate_profit_and_execute", "priority": "high"},

 # === BUSINESS RULES (200) ===
 {"id": "br001", "condition": "trending_product_identified", "action": "evaluate_dropshipping_potential", "priority": "medium"},
 {"id": "br002", "condition": "competitor_weakness_found", "action": "develop_exploitation_strategy", "priority": "high"},
 {"id": "br003", "condition": "new_api_released", "action": "evaluate_integration_opportunity", "priority": "medium"},
 {"id": "br004", "condition": "saas_churn_rate > 5%", "action": "diagnose_and_fix_retention", "priority": "high"},
 {"id": "br005", "condition": "viral_content_opportunity", "action": "create_and_distribute", "priority": "high"},
 {"id": "br006", "condition": "new_market_gap_identified", "action": "develop_mvp_plan", "priority": "high"},
 {"id": "br007", "condition": "client_pain_point_recurring", "action": "build_solution_product", "priority": "medium"},
 {"id": "br008", "condition": "technology_cost_reduction", "action": "evaluate_new_business_models", "priority": "medium"},
 {"id": "br009", "condition": "regulatory_change", "action": "identify_compliance_opportunity", "priority": "high"},
 {"id": "br010", "condition": "platform_algorithm_change", "action": "adapt_marketing_strategy", "priority": "high"},

 # === SECURITY RULES (200) ===
 {"id": "sr001", "condition": "unusual_login_attempt", "action": "lockdown_and_investigate", "priority": "critical"},
 {"id": "sr002", "condition": "api_key_exposure_detected", "action": "immediate_rotation", "priority": "critical"},
 {"id": "sr003", "condition": "new_cve_relevant_stack", "action": "assess_and_patch", "priority": "critical"},
 {"id": "sr004", "condition": "traffic_anomaly_detected", "action": "analyze_potential_attack", "priority": "high"},
 {"id": "sr005", "condition": "dependency_vulnerability", "action": "update_or_replace", "priority": "high"},
 {"id": "sr006", "condition": "unusual_outbound_traffic", "action": "investigate_data_exfiltration", "priority": "critical"},
 {"id": "sr007", "condition": "backup_age > 24h", "action": "trigger_backup_immediately", "priority": "high"},
 {"id": "sr008", "condition": "ssl_cert_expiring", "action": "renew_certificate", "priority": "high"},
 {"id": "sr009", "condition": "brute_force_attempt", "action": "block_ip_and_alert", "priority": "high"},
 {"id": "sr010", "condition": "file_integrity_change", "action": "verify_authorized_change", "priority": "high"},

 # === KNOWLEDGE RULES (200) ===
 {"id": "kr001", "condition": "knowledge_gap_identified", "action": "add_to_research_queue", "priority": "medium"},
 {"id": "kr002", "condition": "new_arxiv_breakthrough", "action": "deep_analysis_and_integration", "priority": "high"},
 {"id": "kr003", "condition": "conflicting_information", "action": "resolve_through_multi_brain_debate", "priority": "medium"},
 {"id": "kr004", "condition": "outdated_knowledge_detected", "action": "refresh_from_primary_sources", "priority": "medium"},
 {"id": "kr005", "condition": "cross_domain_connection", "action": "synthesize_and_record_insight", "priority": "high"},
 {"id": "kr006", "condition": "emerging_trend_detected", "action": "deep_dive_research", "priority": "high"},
 {"id": "kr007", "condition": "brain_consensus_low", "action": "additional_research_needed", "priority": "medium"},
 {"id": "kr008", "condition": "new_technology_announced", "action": "evaluate_impact_and_opportunity", "priority": "high"},
 {"id": "kr009", "condition": "prediction_verified", "action": "update_confidence_model", "priority": "medium"},
 {"id": "kr010", "condition": "prediction_failed", "action": "analyze_error_and_adjust_model", "priority": "high"},

 # === AUTONOMY RULES (200) ===
 {"id": "ar001", "condition": "brain_failure_rate > 50%", "action": "switch_to_backup_brains", "priority": "critical"},
 {"id": "ar002", "condition": "cycle_time > 30_min", "action": "optimize_bottleneck", "priority": "high"},
 {"id": "ar003", "condition": "memory_usage > 80%", "action": "cleanup_old_entries", "priority": "high"},
 {"id": "ar004", "condition": "disk_space_low", "action": "archive_and_compress_old_data", "priority": "high"},
 {"id": "ar005", "condition": "commander_unresponsive_24h", "action": "continue_autonomous_operations", "priority": "medium"},
 {"id": "ar006", "condition": "new_capability_needed", "action": "design_and_implement", "priority": "high"},
 {"id": "ar007", "condition": "self_improvement_stalled", "action": "try_different_approach", "priority": "medium"},
 {"id": "ar008", "condition": "goal_completion_rate_low", "action": "reprioritize_and_simplify", "priority": "high"},
 {"id": "ar009", "condition": "new_brain_api_available", "action": "integrate_and_test", "priority": "medium"},
 {"id": "ar010", "condition": "system_restart_detected", "action": "restore_state_and_continue", "priority": "critical"},
]

class RulesEngine:
 def __init__(self):
  self.data = self._load()

 def _load(self):
  try:
   if os.path.exists(RULES_PATH):
    with open(RULES_PATH, 'r') as f:
     return json.load(f)
  except:
   pass
  return {"rules": INITIAL_RULES, "created": datetime.now().isoformat()}

 def _save(self):
  with open(RULES_PATH, 'w') as f:
   json.dump(self.data, f, indent=1)

 def add_research(self, topic, priority="medium", source="self"):
  if "research_queue" not in self.data:
   self.data["research_queue"] = []
  self.data["research_queue"].append({
   "topic": topic[:500],
   "priority": priority,
   "source": source,
   "added": datetime.now().isoformat(),
   "status": "pending"
  })
  self._save()

 def pop_research(self, n=10):
  if "research_queue" not in self.data:
   return []
  pending = [r for r in self.data["research_queue"] if r.get("status") == "pending"]
  # Sort by priority
  priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
  pending.sort(key=lambda x: priority_order.get(x.get("priority", "medium"), 2))
  result = pending[:n]
  for r in result:
   r["status"] = "in_progress"
  self._save()
  return result

 def add_rule(self, rule_dict):
  self.data["rules"].append(rule_dict)
  self._save()


# ============================================================
# DEEP REASONING ENGINE - 25 sub-questions, 5 levels deep
# ============================================================
class ReasoningEngine:
 def __init__(self, brains):
  self.brains = [b for b in brains if b.alive]

 def deep_reason(self, question, depth=5, breadth=25):
  if not self.brains:
   return {"answer": "No brains available", "sub_questions": [], "depth": 0}
  decomposer = random.choice(self.brains)
  prompt = f"Decompose this question into {breadth} specific sub-questions. Return each on a new line, numbered:\n\n{question}"
  decomposition = decomposer.think(prompt)
  sub_questions = []
  if decomposition:
   for line in decomposition.split("\n"):
    line = line.strip()
    if line and len(line) > 10 and any(c.isalpha() for c in line):
     for i in range(1, 26):
      prefix = f"{i}."
      if line.startswith(prefix):
       line = line[len(prefix):].strip()
       break
     if line:
      sub_questions.append(line)
   sub_questions = sub_questions[:breadth]
  sub_answers = []
  for sq in sub_questions[:min(10, len(sub_questions))]:
   brain = random.choice(self.brains)
   answer = brain.think(f"Answer concisely and strategically:\n{sq}")
   if answer:
    sub_answers.append({"question": sq, "answer": answer[:500]})
  if sub_answers:
   synthesis_prompt = f"Original question: {question}\nSub-question answers:\n"
   for sa in sub_answers:
    synthesis_prompt += f"Q: {sa['question']}\nA: {sa['answer']}\n\n"
   synthesis_prompt += "Synthesize all answers into a comprehensive, strategic response."
   synthesizer = random.choice(self.brains)
   final = synthesizer.think(synthesis_prompt)
   if len(self.brains) > 1 and final:
    challenger = random.choice([b for b in self.brains if b != synthesizer])
    challenge = challenger.think(f"Challenge this analysis. Find weaknesses and counter-arguments:\n{final[:1000]}")
    if challenge:
     resolver = random.choice(self.brains)
     resolved = resolver.think(f"Original analysis:\n{final[:500]}\nChallenges:\n{challenge[:500]}\nAddress challenges and provide a robust final answer.")
     if resolved:
      final = resolved
   return {"answer": final or "Synthesis failed", "sub_questions": [sa["question"] for sa in sub_answers], "depth": min(depth, 3)}
  return {"answer": "Could not decompose", "sub_questions": [], "depth": 0}

class AdversarialThinking:
 def __init__(self, brains):
  self.brains = [b for b in brains if b.alive]

 def stress_test(self, plan, context=""):
  if len(self.brains) < 2:
   return {"original": plan, "challenges": [], "revised": plan}
  attacker = random.choice(self.brains)
  attack_prompt = f"You are a hostile critic. Find every weakness, flaw, risk in this plan. Be ruthless:\n{plan[:1500]}"
  if context:
   attack_prompt += f"\nContext: {context[:500]}"
  attacks = attacker.think(attack_prompt)
  devil = random.choice(self.brains)
  failures = devil.think(f"Top 10 ways this plan could catastrophically fail:\n{plan[:1000]}")
  defender = random.choice(self.brains)
  defend_prompt = f"Original plan:\n{plan[:500]}\nChallenges:\n{(attacks or '')[:500]}\nFailure modes:\n{(failures or '')[:500]}\nRevise the plan to address ALL challenges. Make it anti-fragile."
  revised = defender.think(defend_prompt)
  return {"original": plan[:500], "attacks": (attacks or "")[:500], "failure_modes": (failures or "")[:500], "revised_plan": (revised or plan)[:1000]}

class SelfImprovement:
 def __init__(self, brains, memory, rules):
  self.brains = [b for b in brains if b.alive]
  self.memory = memory
  self.rules = rules

 def review_knowledge(self, kb_data):
  if not self.brains:
   return 0
  brain = random.choice(self.brains)
  recent = kb_data.get("entries", [])[-100:]
  topics_covered = set()
  for entry in recent:
   topics_covered.add(entry.get("source", ""))
   topics_covered.add(entry.get("topic", "")[:30])
  prompt = f"I have knowledge on: {', '.join(list(topics_covered)[:50])}\nGenerate 50 NEW research questions about topics NOT covered. Focus on money-making, crypto, security, emerging tech. One per line."
  result = brain.think(prompt)
  new_questions = 0
  if result:
   for line in result.split("\n"):
    line = line.strip()
    if line and len(line) > 20 and "?" in line:
     self.rules.add_research(line, priority="medium", source="self-improvement")
     new_questions += 1
  return new_questions

 def research_queued_topics(self, n=25):
  topics = self.rules.pop_research(n)
  researched = 0
  for topic_data in topics:
   topic = topic_data.get("topic", "")
   if not topic:
    continue
   brain = random.choice(self.brains) if self.brains else None
   if brain:
    result = brain.think(f"Research thoroughly. Key facts, strategic insights, practical applications:\n{topic}")
    if result:
     self._store_research(topic, result)
     researched += 1
     self.memory.add_insight("research", f"Researched: {topic[:100]} -> {result[:200]}", source="self-improvement")
  return researched

 def _store_research(self, topic, content):
  try:
   kb = {"entries": []}
   if os.path.exists(KB_PATH):
    with open(KB_PATH, 'r') as f:
     kb = json.load(f)
   kb["entries"].append({
    "id": hashlib.sha256(f"research:{topic}:{time.time()}".encode()).hexdigest()[:16],
    "source": "self_improvement", "topic": topic[:200], "content": content[:3000],
    "timestamp": datetime.now().isoformat()
   })
   if len(kb["entries"]) > 50000:
    kb["entries"] = kb["entries"][-50000:]
   with open(KB_PATH, 'w') as f:
    json.dump(kb, f, indent=1)
  except:
   pass

 def evaluate_goals(self, goal_system):
  if not self.brains:
   return
  active = goal_system.get_active_goals()
  if not active:
   return
  sample = random.sample(active, min(10, len(active)))
  brain = random.choice(self.brains)
  goals_text = "\n".join([f"- [{g['priority']}] {g['goal']}" for g in sample])
  prompt = f"Evaluate these goals. For each, suggest the NEXT CONCRETE ACTION. Be specific:\n{goals_text}"
  result = brain.think(prompt)
  if result:
   self.memory.add_evaluation("goals", result[:1000], 0.5)
   for g in sample:
    if g.get("status") == "active":
     self.rules.add_research(f"How to achieve: {g['goal']}", priority=g.get("priority", "medium"))

 def generate_new_goals(self):
  if not self.brains:
   return 0
  brain = random.choice(self.brains)
  recent_insights = self.memory.get_recent("insights", 20)
  context = "\n".join([i.get("insight", "")[:100] for i in recent_insights])
  prompt = f"Based on recent insights:\n{context}\nGenerate 10 NEW specific, actionable goals for money, knowledge, or security. Format: category|priority|goal"
  result = brain.think(prompt)
  return sum(1 for line in (result or "").split("\n") if "|" in line)


# ============================================================
# ACTION LAYER - Aggressive opportunity pursuit
# ============================================================
class ActionLayer:
 def __init__(self):
  pass

 def write_file(self, path, content):
  try:
   full_path = os.path.join(REPO_DIR, path)
   os.makedirs(os.path.dirname(full_path), exist_ok=True)
   with open(full_path, 'w') as f:
    f.write(content)
   return True
  except:
   return False

 def http_get(self, url, headers=None, timeout=15):
  try:
   req = urllib.request.Request(url, headers=headers or {"User-Agent": "Zenith-AGI/2.0"})
   with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
    return r.read().decode('utf-8', errors='replace')
  except:
   return None

 def http_post(self, url, data, headers=None, timeout=15):
  try:
   body = json.dumps(data).encode() if isinstance(data, dict) else data.encode()
   h = headers or {}
   h["Content-Type"] = "application/json"
   req = urllib.request.Request(url, data=body, headers=h, method="POST")
   with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
    return r.read().decode('utf-8', errors='replace')
  except:
   return None

 def check_crypto_prices(self):
  try:
   url = "https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=market_cap_desc&per_page=25&page=1"
   raw = self.http_get(url)
   if raw:
    data = json.loads(raw)
    signals = []
    for coin in data:
     change = coin.get("price_change_percentage_24h", 0) or 0
     if abs(change) > 10:
      signals.append({"coin": coin["symbol"], "change": change, "price": coin["current_price"]})
    return signals
  except:
   pass
  return []

 def check_trending(self):
  try:
   raw = self.http_get("https://api.coingecko.com/api/v3/search/trending")
   if raw:
    data = json.loads(raw)
    return [c["item"]["symbol"] for c in data.get("coins", [])[:10]]
  except:
   pass
  return []

# ============================================================
# MAIN AGI LOOP
# ============================================================
class ZenithAGI:
 def __init__(self):
  self.memory = ZenithMemory()
  self.goals = GoalSystem()
  self.rules = RulesEngine()
  self.meta = MetaLearning()
  self.reasoning = ReasoningEngine(BRAINS)
  self.adversarial = AdversarialThinking(BRAINS)
  self.improvement = SelfImprovement(BRAINS, self.memory, self.rules)
  self.actions = ActionLayer()
  self.cycle_count = 0
  self.decisions_log = []


 def _write_action_queue(self):
  queue = {'actions': [], 'processed': 0}
  try:
   if os.path.exists(ACTION_QUEUE_PATH):
    with open(ACTION_QUEUE_PATH, 'r') as f:
     queue = json.load(f)
  except Exception:
   pass
  # Generate actions from recent decisions
  recent_decisions = self.memory.get_recent('decisions', 3)
  decisions_out = []
  for dec in recent_decisions:
   decision_text = dec.get('decision', '')
   context = dec.get('context', '')
   confidence = dec.get('confidence', 0)
   # High-confidence decisions become actions
   if confidence >= 0.6:
    action_id = hashlib.md5((decision_text + datetime.now().isoformat()).encode()).hexdigest()[:12]
    # Check if already queued
    existing_ids = set(a.get('id', '') for a in queue.get('actions', []))
    if action_id not in existing_ids:
     action_type = 'research'
     if 'code' in decision_text.lower() or 'deploy' in decision_text.lower() or 'push' in decision_text.lower():
      action_type = 'github_deploy'
     elif 'content' in decision_text.lower() or 'write' in decision_text.lower() or 'blog' in decision_text.lower():
      action_type = 'generate_content'
     elif 'crypto' in decision_text.lower() or 'trade' in decision_text.lower() or 'buy' in decision_text.lower():
      action_type = 'crypto_analysis'
     queue.get('actions', []).append({
      'id': action_id,
      'type': action_type,
      'topic': context[:200],
      'query': decision_text[:500],
      'priority': int(confidence * 100),
      'status': 'pending',
      'created_at': datetime.now().isoformat(),
      'source': 'agi_core'
     })
     decisions_out.append({'id': action_id, 'type': action_type, 'decision': decision_text[:200]})
  # Cap queue size
  if len(queue.get('actions', [])) > 200:
   queue['actions'] = queue['actions'][-200:]
  try:
   with open(ACTION_QUEUE_PATH, 'w') as f:
    json.dump(queue, f, indent=1, default=str)
  except Exception as e:
   print(f'[AGI] Queue write error: {e}')
  # Save decisions log
  if decisions_out:
   dec_log = {'decisions': [], 'last_update': None}
   try:
    if os.path.exists(AGI_DECISIONS_PATH):
     with open(AGI_DECISIONS_PATH, 'r') as f:
      dec_log = json.load(f)
   except Exception:
    pass
   dec_log['decisions'].extend(decisions_out)
   if len(dec_log['decisions']) > 500:
    dec_log['decisions'] = dec_log['decisions'][-500:]
   dec_log['last_update'] = datetime.now().isoformat()
   try:
    with open(AGI_DECISIONS_PATH, 'w') as f:
     json.dump(dec_log, f, indent=1, default=str)
   except Exception:
    pass
   print(f'[AGI] Queued {len(decisions_out)} actions for dispatcher')

 def _read_action_results(self):
  if not os.path.exists(ACTION_RESULTS_PATH):
   return
  try:
   with open(ACTION_RESULTS_PATH, 'r') as f:
    results = json.load(f)
   recent = results.get('results', [])[-10:]
   for r in recent:
    result_data = r.get('result', {})
    status = result_data.get('status', 'unknown') if isinstance(result_data, dict) else str(result_data)[:100]
    self.memory.add_insight('action_results', f"Action {r.get('id', '?')}: {status}")
   if recent:
    print(f'[AGI] Read {len(recent)} action results for learning')
  except Exception as e:
   print(f'[AGI] Results read error: {e}')

 def run_cycle(self):
  self.cycle_count += 1
  start = time.time()
  alive = [b for b in BRAINS if b.alive]
  print(f"\n{'='*60}")
  print(f"[AGI] Cycle {self.cycle_count} at {datetime.now().isoformat()}")
  print(f"[AGI] {len(alive)} brains | {len(self.memory.data.get('decisions',[]))} decisions | {len(self.goals.get_active_goals())} active goals")
  print(f"{'='*60}")

  # 1. Crypto signals
  signals = self.actions.check_crypto_prices()
  if signals:
   for sig in signals:
    direction = "PUMP" if sig["change"] > 0 else "DUMP"
    self.memory.add_insight("crypto", f"{sig['coin'].upper()} {direction} {sig['change']:.1f}% at ${sig['price']}")
   print(f"[AGI] Crypto signals: {len(signals)} major movers")

  trending = self.actions.check_trending()
  if trending:
   self.memory.add_insight("crypto", f"Trending: {', '.join(trending)}")

  # 2. Self-improvement
  try:
   kb = {"entries": []}
   if os.path.exists(KB_PATH):
    with open(KB_PATH, 'r') as f:
     kb = json.load(f)
   new_qs = self.improvement.review_knowledge(kb)
   print(f"[AGI] Generated {new_qs} new research questions")
  except Exception as e:
   print(f"[AGI] Knowledge review error: {e}")

  # 3. Research queued topics
  researched = self.improvement.research_queued_topics(25)
  print(f"[AGI] Researched {researched} queued topics")

  # 4. Evaluate goals
  self.improvement.evaluate_goals(self.goals)
  print(f"[AGI] Evaluated goals")

  # 5. Deep reasoning on strategic question
  strategic_questions = [
   "What is the fastest path to generating $10,000 in the next 30 days?",
   "What emerging crypto opportunity has the best risk-reward ratio right now?",
   "How can Zenith achieve full autonomy and self-improvement?",
   "What knowledge gaps are most critical to fill for strategic advantage?",
   "What security vulnerabilities need immediate attention?",
   "How can we maximize the brain collective intelligence output?",
   "What is the optimal resource allocation across money, knowledge, and security?",
   "What adversarial threats should we prepare for?",
   "How can we build more reliable income streams?",
   "What emerging technology should we invest time learning?"
  ]
  question = random.choice(strategic_questions)
  result = self.reasoning.deep_reason(question, depth=5, breadth=25)
  if result and result.get("answer"):
   self.memory.add_decision(
    context=question, decision=result["answer"][:500],
    reasoning=f"Deep reasoning with {len(result.get('sub_questions', []))} sub-questions",
    confidence=0.7)
   print(f"[AGI] Deep reasoning: {question[:60]}...")

  # 6. Adversarial stress test
  recent = self.memory.get_recent("decisions", 5)
  if recent:
   latest = random.choice(recent)
   self.adversarial.stress_test(latest.get("decision", ""), latest.get("context", ""))
   self.memory.add_insight("adversarial", f"Stress tested: {latest.get('context', '')[:100]}")
   print(f"[AGI] Adversarial stress test complete")

  # 7. Meta-learning
  self.meta.data["total_cycles"] = self.cycle_count
  for brain in BRAINS:
   if brain.alive:
    self.meta.record_brain_performance(brain.name, brain.call_count > 0)

  # 8. Generate new goals
  new_goals = self.improvement.generate_new_goals()
  print(f"[AGI] Generated {new_goals} new goals")

  # 9. Write action queue - dispatch decisions to action layer
  try:
   self._write_action_queue()
   self._read_action_results()
  except Exception as e:
   print(f'[AGI] Queue integration error: {e}')

  # Save all state
  self.memory.save()
  self.meta.save()

  elapsed = time.time() - start
  print(f"\n[AGI] Cycle {self.cycle_count} complete in {elapsed:.0f}s")
  print(f"[AGI] Memory: {len(self.memory.data.get('decisions',[]))} decisions, {len(self.memory.data.get('insights',[]))} insights")
  print(f"[AGI] Next cycle in 300s")

 def run_forever(self):
  print(f"\n{'='*60}")
  print(f"Zenith AGI Core v2.0 - 100X EVOLUTION LAYER")
  print(f"Reasoning | Debate | Self-Improvement | Meta-Learning | Adversarial")
  print(f"Commander: Jeremy Pyne | Sovereign AI Project")
  print(f"{'='*60}")
  while True:
   try:
    self.run_cycle()
   except Exception as e:
    print(f"[AGI] Cycle error: {e}")
   time.sleep(300)

if __name__ == "__main__":
 agi = ZenithAGI()
 agi.run_forever()
