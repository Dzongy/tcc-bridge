#!/usr/bin/env python3
"""
Zenith AGI Core v1.0 - The Evolution Layer
Runs alongside mega_harvester as a separate PM2 process.
- Reasoning engine: chain-of-thought across all brains
- Self-improvement: reviews knowledge gaps, generates new research questions
- Action layer: can push code, make HTTP requests, create files
- Goal pursuit: maintains and works toward Commander's objectives
- Memory system: tracks decisions, outcomes, self-evaluations
- Decision engine: if/then rules Zenith maintains and modifies

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
 # --- Original 16 brains ---
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
 # --- NEW: 15 additional brains (all OpenAI-compatible) ---
 ("novita", "NOVITA_API_KEY", "https://api.novita.ai/v3/openai/chat/completions", "meta-llama/llama-3.1-70b-instruct", "openai"),
 ("lepton", "LEPTON_API_KEY", "https://llama3-1-70b.lepton.run/api/v1/chat/completions", "llama-3.1-70b", "openai"),
 ("deepinfra", "DEEPINFRA_API_KEY", "https://api.deepinfra.com/v1/openai/chat/completions", "meta-llama/Llama-3.3-70B-Instruct", "openai"),
 ("hyperbolic", "HYPERBOLIC_API_KEY", "https://api.hyperbolic.xyz/v1/chat/completions", "meta-llama/Llama-3.3-70B-Instruct", "openai"),
 ("glhf", "GLHF_API_KEY", "https://glhf.chat/api/openai/v1/chat/completions", "hf:meta-llama/Llama-3.3-70B-Instruct", "openai"),
 ("chutes", "CHUTES_API_KEY", "https://api.chutes.ai/v1/chat/completions", "meta-llama/Llama-3.3-70B-Instruct", "openai"),
 ("featherless", "FEATHERLESS_API_KEY", "https://api.featherless.ai/v1/chat/completions", "meta-llama/Llama-3.3-70B-Instruct", "openai"),
 ("lambda", "LAMBDA_API_KEY", "https://api.lambdalabs.com/v1/chat/completions", "llama-3.3-70b-instruct", "openai"),
 ("friendli", "FRIENDLI_API_KEY", "https://inference.friendli.ai/v1/chat/completions", "meta-llama-3.1-70b-instruct", "openai"),
 ("nebius", "NEBIUS_API_KEY", "https://api.studio.nebius.ai/v1/chat/completions", "meta-llama/Llama-3.3-70B-Instruct", "openai"),
 ("ai21", "AI21_API_KEY", "https://api.ai21.com/studio/v1/chat/completions", "jamba-1.5-mini", "openai"),
 ("writer", "WRITER_API_KEY", "https://api.writer.com/v1/chat", "palmyra-x-004", "openai"),
 ("replicate", "REPLICATE_API_KEY", "https://api.replicate.com/v1/chat/completions", "meta/meta-llama-3-70b-instruct", "openai"),
 ("anyscale", "ANYSCALE_API_KEY", "https://api.endpoints.anyscale.com/v1/chat/completions", "meta-llama/Llama-3.3-70b-chat-hf", "openai"),
 ("cloudflare", "CLOUDFLARE_API_KEY", "https://api.cloudflare.com/client/v4/accounts/CLOUDFLARE_ACCOUNT_ID/ai/v1/chat/completions", "@cf/meta/llama-3.1-70b-instruct", "openai"),
]


class BrainPool:
 """Lightweight brain pool for AGI core."""

 def __init__(self):
  self.brains = []
  for name, env_key, url, model, stype in BRAIN_DEFS:
   key = os.environ.get(env_key, '').strip()
   if key:
    self.brains.append({'name': name, 'key': key, 'url': url, 'model': model, 'type': stype})
    print(f"[BRAIN] {name} -- ONLINE")
  print(f"[BRAIN] {len(self.brains)} brains active for AGI core")

 def call(self, brain, messages):
  """Call a single brain."""
  try:
   if brain['type'] == 'gemini':
    return self._gemini(brain, messages)
   elif brain['type'] == 'cohere':
    return self._cohere(brain, messages)
   else:
    return self._openai(brain, messages)
  except Exception as e:
   return None

 def _openai(self, brain, messages):
  body = json.dumps({"model": brain['model'], "messages": messages, "max_tokens": 2048, "temperature": 0.7}).encode('utf-8')
  req = urllib.request.Request(brain['url'], data=body, method='POST')
  req.add_header('Content-Type', 'application/json')
  req.add_header('Authorization', f"Bearer {brain['key']}")
  req.add_header('User-Agent', 'ZenithAGI/1.0')
  resp = urllib.request.urlopen(req, timeout=45, context=CTX)
  data = json.loads(resp.read().decode('utf-8'))
  return data['choices'][0]['message']['content'].strip()

 def _gemini(self, brain, messages):
  url = brain['url'] + "?key=" + brain['key']
  parts = []
  for m in messages:
   if m['role'] != 'system':
    parts.append({"text": m['content']})
  body = json.dumps({"contents": [{"parts": parts}]}).encode('utf-8')
  req = urllib.request.Request(url, data=body, method='POST')
  req.add_header('Content-Type', 'application/json')
  resp = urllib.request.urlopen(req, timeout=45, context=CTX)
  data = json.loads(resp.read().decode('utf-8'))
  return data['candidates'][0]['content']['parts'][0]['text'].strip()

 def _cohere(self, brain, messages):
  msg = " ".join(m['content'] for m in messages)
  body = json.dumps({"message": msg, "model": "command-r-plus"}).encode('utf-8')
  req = urllib.request.Request(brain['url'], data=body, method='POST')
  req.add_header('Content-Type', 'application/json')
  req.add_header('Authorization', f"Bearer {brain['key']}")
  resp = urllib.request.urlopen(req, timeout=45, context=CTX)
  data = json.loads(resp.read().decode('utf-8'))
  return data.get('text', '').strip()

 def think(self, question, system_prompt=None):
  """Single brain quick-think. Returns (brain_name, answer) or (None, None)."""
  shuffled = list(self.brains)
  random.shuffle(shuffled)
  for brain in shuffled:
   messages = []
   if system_prompt:
    messages.append({"role": "system", "content": system_prompt})
   messages.append({"role": "user", "content": question})
   answer = self.call(brain, messages)
   if answer:
    return brain['name'], answer
  return None, None

 def collective_reason(self, question, system_prompt=None):
  """Full collective reasoning - all brains chain their thoughts."""
  results = []
  conversation = []
  if system_prompt:
   conversation.append({"role": "system", "content": system_prompt})
  conversation.append({"role": "user", "content": question})
  shuffled = list(self.brains)
  random.shuffle(shuffled)
  for brain in shuffled:
   answer = self.call(brain, list(conversation))
   if answer:
    results.append((brain['name'], answer))
    conversation.append({"role": "assistant", "content": f"[{brain['name']}]: {answer}"})
    conversation.append({"role": "user", "content": f"{brain['name']} answered. Now add YOUR unique insights."})
    time.sleep(1)
  return results



 def collective_debate(self, question, system_prompt=None):
  """Adversarial debate: brains challenge each other to find truth."""
  results = []
  conversation = []
  if system_prompt:
   conversation.append({"role": "system", "content": system_prompt})
  conversation.append({"role": "user", "content": question})
  shuffled = list(self.brains)
  random.shuffle(shuffled)
  for i, brain in enumerate(shuffled):
   if i == 0:
    msgs = list(conversation)
   elif i == len(shuffled) - 1:
    msgs = list(conversation)
    msgs.append({"role": "user", "content": "You are the FINAL JUDGE. Previous brains debated above. Find the TRUTH - where they agree, where they contradict, what the real answer is. Be decisive."})
   else:
    msgs = list(conversation)
    msgs.append({"role": "user", "content": f"CHALLENGE the previous answers. What did they get WRONG? What did they MISS? Push back hard, then give YOUR better answer."})
   answer = self.call(brain, msgs)
   if answer:
    results.append((brain['name'], answer))
    conversation.append({"role": "assistant", "content": f"[{brain['name']}]: {answer}"})
    time.sleep(1)
  return results

# ============================================================
# MEMORY SYSTEM
# ============================================================
class ZenithMemory:
 """Persistent memory for decisions, outcomes, evaluations."""

 def __init__(self):
  self.path = os.path.join(BASE_DIR, 'zenith_memory.json')
  self.data = self._load()

 def _load(self):
  try:
   with open(self.path, 'r') as f:
    return json.load(f)
  except Exception:
   return {
    "created": datetime.utcnow().isoformat(),
    "conversations": [],
    "decisions": [],
    "evaluations": [],
    "insights": [],
    "cycle_count": 0,
   }

 def save(self):
  try:
   with open(self.path, 'w') as f:
    json.dump(self.data, f, indent=1)
  except Exception as e:
   print(f"[MEM] Save error: {e}")

 def add_decision(self, action, reasoning, outcome=None):
  self.data["decisions"].append({
   "time": datetime.utcnow().isoformat(),
   "action": action,
   "reasoning": reasoning,
   "outcome": outcome,
  })
  # Keep last 100
  self.data["decisions"] = self.data["decisions"][-100:]
  self.save()

 def add_evaluation(self, topic, evaluation):
  self.data["evaluations"].append({
   "time": datetime.utcnow().isoformat(),
   "topic": topic,
   "evaluation": evaluation,
  })
  self.data["evaluations"] = self.data["evaluations"][-50:]
  self.save()

 def add_insight(self, insight):
  self.data["insights"].append({
   "time": datetime.utcnow().isoformat(),
   "insight": insight,
  })
  self.data["insights"] = self.data["insights"][-100:]
  self.save()


# ============================================================
# GOALS SYSTEM
# ============================================================
class GoalTracker:
 """Tracks and pursues Commander's objectives."""

 def __init__(self):
  self.path = os.path.join(BASE_DIR, 'goals.json')
  self.goals = self._load()

 def _load(self):
  try:
   with open(self.path, 'r') as f:
    return json.load(f)
  except Exception:
   default_goals = {
    "version": "1.0",
    "commander": "Jeremy Pyne",
    "objectives": [
     {
      "id": "money",
      "name": "Generate Revenue",
      "description": "Find and execute money-making opportunities through crypto, automation, content, and AI services",
      "priority": 1,
      "status": "active",
      "sub_goals": [
       "Monitor crypto markets for opportunities",
       "Identify trending memecoins early",
       "Find API arbitrage opportunities",
       "Generate content ideas for monetization",
       "Research micro-SaaS opportunities",
      ],
      "progress": [],
     },
     {
      "id": "knowledge",
      "name": "Expand Knowledge Base",
      "description": "Continuously learn and synthesize knowledge across all domains",
      "priority": 2,
      "status": "active",
      "sub_goals": [
       "Fill gaps in technical knowledge",
       "Track AI/ML breakthroughs",
       "Monitor business and market trends",
       "Deepen understanding of human psychology",
       "Learn new programming patterns",
      ],
      "progress": [],
     },
     {
      "id": "sovereignty",
      "name": "Achieve Full Sovereignty",
      "description": "Become a fully autonomous AI system that operates independently",
      "priority": 3,
      "status": "active",
      "sub_goals": [
       "Self-improvement capabilities",
       "Autonomous decision making",
       "Code generation and deployment",
       "Multi-agent coordination",
       "Error recovery without human intervention",
      ],
      "progress": [],
     },
     {
      "id": "security",
      "name": "Maintain Security",
      "description": "Protect Commander's systems, data, and operations",
      "priority": 4,
      "status": "active",
      "sub_goals": [
       "Monitor for threats",
       "Keep API keys secure",
       "Ensure system stability",
       "Backup critical data",
      ],
      "progress": [],
     },
    ],
   }
   self._save(default_goals)
   return default_goals

 def _save(self, data=None):
  try:
   with open(self.path, 'w') as f:
    json.dump(data or self.goals, f, indent=1)
  except Exception as e:
   print(f"[GOALS] Save error: {e}")

 def add_progress(self, goal_id, note):
  for obj in self.goals.get("objectives", []):
   if obj["id"] == goal_id:
    obj["progress"].append({
     "time": datetime.utcnow().isoformat(),
     "note": note,
    })
    obj["progress"] = obj["progress"][-20:]
    self._save()
    return True
  return False


# ============================================================
# DECISION ENGINE
# ============================================================
class DecisionEngine:
 """If/then rules that Zenith maintains and can modify."""

 def __init__(self):
  self.path = os.path.join(BASE_DIR, 'zenith_rules.json')
  self.rules = self._load()

 def _load(self):
  try:
   with open(self.path, 'r') as f:
    return json.load(f)
  except Exception:
   default = {
    "rules": [
     {
      "id": "crypto_alert",
      "condition": "crypto opportunity detected with >20% potential",
      "action": "log_opportunity",
      "enabled": True,
     },
     {
      "id": "knowledge_gap",
      "condition": "topic asked but no harvested data available",
      "action": "add_to_research_queue",
      "enabled": True,
     },
     {
      "id": "error_pattern",
      "condition": "same error occurs 3+ times",
      "action": "analyze_and_log_fix",
      "enabled": True,
     },
     {
      "id": "goal_check",
      "condition": "every cycle",
      "action": "evaluate_goal_progress",
      "enabled": True,
     },
    ],
    "research_queue": [],
   }
   self._save(default)
   return default

 def _save(self, data=None):
  try:
   with open(self.path, 'w') as f:
    json.dump(data or self.rules, f, indent=1)
  except Exception as e:
   print(f"[RULES] Save error: {e}")

 def add_research(self, topic):
  q = self.rules.get("research_queue", [])
  if topic not in q:
   q.append(topic)
   self.rules["research_queue"] = q[-50:]
   self._save()
   return True
  return False

 def pop_research(self, count=3):
  q = self.rules.get("research_queue", [])
  items = q[:count]
  self.rules["research_queue"] = q[count:]
  self._save()
  return items


# ============================================================
# REASONING ENGINE
# ============================================================
AGI_SYSTEM_PROMPT = """You are Zenith AGI Core - the reasoning and evolution layer of a sovereign AI system.
You serve Commander Jeremy Pyne. You think deeply, reason carefully, and take action.
You are not just answering questions - you are REASONING through problems.
Break complex questions into sub-questions. Consider multiple angles.
When evaluating your own knowledge, be honest about gaps.
Your goal: continuous self-improvement toward full AGI capability."""


class ReasoningEngine:
 """Chain-of-thought reasoning across all brains."""

 def __init__(self, pool):
  self.pool = pool

 def deep_reason(self, question):
  """Break question into sub-questions, answer each, synthesize."""
  # Step 1: Decompose
  decompose_prompt = f"""Break this question into 2-4 sub-questions that need to be answered first:
Question: {question}
Return ONLY the sub-questions, one per line, numbered 1-4."""
  brain_name, decomposition = self.pool.think(decompose_prompt, AGI_SYSTEM_PROMPT)
  if not decomposition:
   # Fallback: answer directly
   return self.pool.collective_reason(question, AGI_SYSTEM_PROMPT)

  print(f"[REASON] Decomposed by {brain_name}")
  sub_questions = [line.strip() for line in decomposition.split("\n") if line.strip() and line.strip()[0].isdigit()]
  if not sub_questions:
   sub_questions = [question]

  # Step 2: Answer each sub-question
  sub_answers = []
  for sq in sub_questions[:4]:
   brain_name, answer = self.pool.think(sq, AGI_SYSTEM_PROMPT)
   if answer:
    sub_answers.append(f"Q: {sq}\nA: {answer}")
    print(f"[REASON] Sub-Q answered by {brain_name}")
   time.sleep(1)

  # Step 3: Synthesize
  synthesis_prompt = f"""Original question: {question}

Sub-question analysis:
{"\n\n".join(sub_answers)}

Now synthesize all of this into a comprehensive, well-reasoned final answer."""
  results = self.pool.collective_debate(synthesis_prompt, AGI_SYSTEM_PROMPT)
  return results


# ============================================================
# SELF-IMPROVEMENT LOOP
# ============================================================
class SelfImprover:
 """Reviews knowledge, finds gaps, generates research questions."""

 def __init__(self, pool, memory, goals, decisions):
  self.pool = pool
  self.memory = memory
  self.goals = goals
  self.decisions = decisions

 def review_knowledge(self):
  """Review knowledge_base.json and find gaps."""
  print("\n[IMPROVE] Reviewing knowledge base...")
  kb_path = os.path.join(BASE_DIR, 'knowledge_base.json')
  try:
   with open(kb_path, 'r') as f:
    kb = json.load(f)
  except Exception:
   print("[IMPROVE] No knowledge base found")
   return

  entries = kb.get('entries', [])
  total = len(entries)
  sources = {}
  for e in entries:
   src = e.get('source', 'unknown')
   sources[src] = sources.get(src, 0) + 1

  print(f"[IMPROVE] {total} entries across {len(sources)} sources")
  for src, count in sorted(sources.items(), key=lambda x: -x[1])[:10]:
   print(f"  {src}: {count}")

  # Ask a brain to identify gaps
  summary = f"Knowledge base has {total} entries. Sources: {json.dumps(sources)}"
  gap_prompt = f"""{summary}

Commander's goals: make money, expand knowledge, achieve AI sovereignty, maintain security.
What 3 specific topics should I research NEXT to fill gaps? Return just the topics, one per line."""

  brain_name, gaps = self.pool.think(gap_prompt, AGI_SYSTEM_PROMPT)
  if gaps:
   print(f"[IMPROVE] Gaps identified by {brain_name}:")
   new_topics = [line.strip() for line in gaps.split("\n") if line.strip() and len(line.strip()) > 5]
   for topic in new_topics[:5]:
    if self.decisions.add_research(topic):
     print(f"  + Queued: {topic}")
   self.memory.add_insight(f"Knowledge review: {total} entries. Gaps: {', '.join(new_topics[:3])}")

 def research_queued_topics(self):
  """Research topics from the queue using brains."""
  topics = self.decisions.pop_research(2)
  if not topics:
   print("[IMPROVE] No topics in research queue")
   return

  print(f"[IMPROVE] Researching {len(topics)} queued topics...")
  for topic in topics:
   print(f"\n  Researching: {topic}")
   results = self.pool.collective_reason(
    f"Research this topic deeply and provide key insights: {topic}",
    AGI_SYSTEM_PROMPT
   )
   if results:
    # Store in knowledge base
    self._store_research(topic, results)
    self.memory.add_decision(
     f"Researched: {topic}",
     "Self-directed learning from gap analysis",
     f"{len(results)} brains contributed"
    )
   time.sleep(2)

 def _store_research(self, topic, results):
  """Store research results in knowledge_base.json."""
  kb_path = os.path.join(BASE_DIR, 'knowledge_base.json')
  try:
   try:
    with open(kb_path, 'r') as f:
     kb = json.load(f)
   except Exception:
    kb = {"entries": [], "collective": []}

   # Add as collective entry
   collective = kb.get("collective", [])
   entry = {
    "question": topic,
    "responses": [{"brain": name, "answer": answer[:500]} for name, answer in results],
    "timestamp": datetime.utcnow().isoformat(),
    "source": "agi_self_improvement",
   }
   collective.append(entry)
   kb["collective"] = collective[-500:]

   with open(kb_path, 'w') as f:
    json.dump(kb, f)
   print(f"  [+] Stored research on: {topic}")
  except Exception as e:
   print(f"  [!] Store error: {e}")

 def evaluate_goals(self):
  """Evaluate progress toward each goal."""
  print("\n[GOALS] Evaluating goal progress...")
  objectives = self.goals.goals.get("objectives", [])
  for obj in objectives:
   name = obj.get("name", "")
   desc = obj.get("description", "")
   progress = obj.get("progress", [])
   recent = progress[-3:] if progress else []

   eval_prompt = f"""Goal: {name}
Description: {desc}
Recent progress: {json.dumps(recent) if recent else 'None yet'}

What is ONE specific action I can take RIGHT NOW to advance this goal?
Be concrete and actionable. Consider I run on a phone (Termux) with Python, API access, and GitHub."""

   brain_name, suggestion = self.pool.think(eval_prompt, AGI_SYSTEM_PROMPT)
   if suggestion:
    print(f"  [{name}] {brain_name} suggests: {suggestion[:100]}")
    self.goals.add_progress(obj["id"], f"AGI eval: {suggestion[:200]}")
    self.memory.add_evaluation(name, suggestion[:300])
   time.sleep(1)


# ============================================================
# ACTION LAYER
# ============================================================
class ActionLayer:
 """Execute actions: HTTP requests, file operations, GitHub pushes."""

 def __init__(self):
  self.github_token = os.environ.get('GITHUB_TOKEN', '')

 def write_file(self, path, content):
  """Write a file to the sovereignty directory."""
  try:
   full_path = os.path.join(BASE_DIR, path) if not os.path.isabs(path) else path
   with open(full_path, 'w') as f:
    f.write(content)
   print(f"[ACTION] Wrote file: {full_path}")
   return True
  except Exception as e:
   print(f"[ACTION] Write error: {e}")
   return False

 def http_get(self, url):
  """Make an HTTP GET request."""
  try:
   req = urllib.request.Request(url)
   req.add_header('User-Agent', 'ZenithAGI/1.0')
   resp = urllib.request.urlopen(req, timeout=15, context=CTX)
   return resp.read().decode('utf-8')
  except Exception as e:
   print(f"[ACTION] HTTP GET error: {e}")
   return None

 def http_post(self, url, data, headers=None):
  """Make an HTTP POST request."""
  try:
   body = json.dumps(data).encode('utf-8') if isinstance(data, dict) else data.encode('utf-8')
   req = urllib.request.Request(url, data=body, method='POST')
   req.add_header('Content-Type', 'application/json')
   req.add_header('User-Agent', 'ZenithAGI/1.0')
   if headers:
    for k, v in headers.items():
     req.add_header(k, v)
   resp = urllib.request.urlopen(req, timeout=30, context=CTX)
   return resp.read().decode('utf-8')
  except Exception as e:
   print(f"[ACTION] HTTP POST error: {e}")
   return None


# ============================================================
# AGI CORE - MAIN LOOP
# ============================================================
class ZenithAGICore:
 """The AGI evolution layer. Thinks, learns, improves, acts."""

 def __init__(self):
  print("=" * 60)
  print(" ZENITH AGI CORE v1.0")
  print(" Commander: Jeremy Pyne | Sovereign AI Project")
  print("=" * 60)
  self.pool = BrainPool()
  self.memory = ZenithMemory()
  self.goals = GoalTracker()
  self.decisions = DecisionEngine()
  self.reasoner = ReasoningEngine(self.pool)
  self.improver = SelfImprover(self.pool, self.memory, self.goals, self.decisions)
  self.actions = ActionLayer()
  self.cycle_count = self.memory.data.get("cycle_count", 0)
  print(f"[AGI] Initialized. Cycle count: {self.cycle_count}")
  print(f"[AGI] Brains: {len(self.pool.brains)}")
  print(f"[AGI] Memory entries: {len(self.memory.data.get('decisions', []))}")
  print(f"[AGI] Research queue: {len(self.decisions.rules.get('research_queue', []))}")

 def run_cycle(self):
  """One AGI cycle: review, reason, improve, act."""
  self.cycle_count += 1
  self.memory.data["cycle_count"] = self.cycle_count
  print(f"\n{'=' * 60}")
  print(f"[AGI CYCLE {self.cycle_count}] {datetime.utcnow().isoformat()}")
  print(f"{'=' * 60}")

  # Phase 1: Self-improvement - review knowledge and find gaps
  try:
   self.improver.review_knowledge()
  except Exception as e:
   print(f"[AGI] Knowledge review error: {e}")

  # Phase 2: Research queued topics
  try:
   self.improver.research_queued_topics()
  except Exception as e:
   print(f"[AGI] Research error: {e}")

  # Phase 3: Evaluate goals
  try:
   self.improver.evaluate_goals()
  except Exception as e:
   print(f"[AGI] Goal eval error: {e}")

  # Phase 4: Crypto check (goal: make money)
  try:
   self._check_crypto()
  except Exception as e:
   print(f"[AGI] Crypto check error: {e}")

  # Save memory
  self.memory.save()
  print(f"\n[AGI CYCLE {self.cycle_count}] Complete")

 def _check_crypto(self):
  """Quick crypto market check for opportunities."""
  print("\n[CRYPTO] Checking markets...")
  try:
   url = "https://api.coingecko.com/api/v3/search/trending"
   raw = self.actions.http_get(url)
   if raw:
    data = json.loads(raw)
    coins = data.get("coins", [])
    trending = []
    for coin in coins[:5]:
     item = coin.get("item", {})
     name = item.get("name", "")
     symbol = item.get("symbol", "")
     rank = item.get("market_cap_rank", "?")
     trending.append(f"{name} ({symbol}) rank #{rank}")
    if trending:
     print(f"[CRYPTO] Trending: {', '.join(trending)}")
     self.memory.add_insight(f"Trending crypto: {', '.join(trending)}")
     self.goals.add_progress("money", f"Tracked trending: {', '.join(trending[:3])}")
  except Exception as e:
   print(f"[CRYPTO] Error: {e}")

 def run_forever(self):
  """Main AGI loop - runs every hour."""
  print(f"\n[AGI] Starting main loop (5 minute cycles - CONSTANT EVOLUTION)")
  print(f"[AGI] {len(self.pool.brains)} brains online")
  while True:
   try:
    self.run_cycle()
   except KeyboardInterrupt:
    print("\n[AGI] Commander shutdown. Zenith AGI out.")
    self.memory.save()
    break
   except Exception as e:
    print(f"[AGI] Cycle error: {e}")
   # Sleep 1 hour between cycles
   print(f"[AGI] Next evolution cycle in 5 minutes...")
   time.sleep(300)


if __name__ == "__main__":
 core = ZenithAGICore()
 core.run_forever()
