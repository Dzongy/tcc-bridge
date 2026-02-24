#!/usr/bin/env python3
"""
Zenith Universal Action Dispatcher v1.0
THE ACTION LAYER - Turns Zenith from a thinker into a DOER.

Runs as PM2 process alongside mega_harvester and agi_core.
60-second cycles: check queue -> execute actions -> generate content -> crypto signals -> reports

Commander: Jeremy Pyne | Sovereign AI Project
pm2 start sovereignty/action_dispatcher.py --name dispatch --interpreter python3
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
import base64
import re
from datetime import datetime, timedelta

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

# --- Paths ---
REPO_DIR = os.path.dirname(os.path.abspath(__file__))
KB_PATH = os.path.join(REPO_DIR, 'knowledge_base.json')
ACTION_QUEUE_PATH = os.path.join(REPO_DIR, 'action_queue.json')
ACTION_RESULTS_PATH = os.path.join(REPO_DIR, 'action_results.json')
ACTION_LOG_PATH = os.path.join(REPO_DIR, 'action_log.json')
ACTION_STATUS_PATH = os.path.join(REPO_DIR, 'action_status.json')
CRYPTO_SIGNALS_PATH = os.path.join(REPO_DIR, 'crypto_signals.json')
API_REGISTRY_PATH = os.path.join(REPO_DIR, 'api_registry.json')
COMMANDER_BRIEFING_PATH = os.path.join(REPO_DIR, 'commander_briefing.json')
CONTENT_DIR = os.path.join(REPO_DIR, 'content')
REPORTS_DIR = os.path.join(REPO_DIR, 'reports')

# GitHub config
GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN', '')
GITHUB_REPO = 'Dzongy/tcc-bridge'
GITHUB_API = 'https://api.github.com'

# Ensure directories exist
for d in [CONTENT_DIR, REPORTS_DIR,
          os.path.join(CONTENT_DIR, 'blog'),
          os.path.join(CONTENT_DIR, 'tweets'),
          os.path.join(CONTENT_DIR, 'articles')]:
 os.makedirs(d, exist_ok=True)

# --- SSL context ---
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

# --- Brain scanning (same pattern as mega_harvester) ---
BRAIN_CONFIGS = {
 'gemini': {
  'url': 'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent',
  'key_env': 'GEMINI_API_KEY',
  'auth': 'query',
  'model': None
 },
 'openrouter': {
  'url': 'https://openrouter.ai/api/v1/chat/completions',
  'key_env': 'OPENROUTER_API_KEY',
  'auth': 'bearer',
  'model': 'qwen/qwen3-next-80b-a3b-instruct:free'
 },
 'cohere': {
  'url': 'https://api.cohere.ai/v2/chat',
  'key_env': 'CO_API_KEY',
  'auth': 'bearer',
  'model': 'command-r-plus'
 },
 'groq': {
  'url': 'https://api.groq.com/openai/v1/chat/completions',
  'key_env': 'GROQ_API_KEY',
  'auth': 'bearer',
  'model': 'llama-3.3-70b-versatile'
 },
 'deepseek': {
  'url': 'https://api.deepseek.com/v1/chat/completions',
  'key_env': 'DEEPSEEK_API_KEY',
  'auth': 'bearer',
  'model': 'deepseek-chat'
 },
 'together': {
  'url': 'https://api.together.xyz/v1/chat/completions',
  'key_env': 'TOGETHER_API_KEY',
  'auth': 'bearer',
  'model': 'meta-llama/Llama-3.3-70B-Instruct-Turbo'
 },
 'mistral': {
  'url': 'https://api.mistral.ai/v1/chat/completions',
  'key_env': 'MISTRAL_API_KEY',
  'auth': 'bearer',
  'model': 'mistral-large-latest'
 },
 'fireworks': {
  'url': 'https://api.fireworks.ai/inference/v1/chat/completions',
  'key_env': 'FIREWORKS_API_KEY',
  'auth': 'bearer',
  'model': 'accounts/fireworks/models/llama-v3p3-70b-instruct'
 },
 'cerebras': {
  'url': 'https://api.cerebras.ai/v1/chat/completions',
  'key_env': 'CEREBRAS_API_KEY',
  'auth': 'bearer',
  'model': 'llama-3.3-70b'
 },
 'sambanova': {
  'url': 'https://api.sambanova.ai/v1/chat/completions',
  'key_env': 'SAMBANOVA_API_KEY',
  'auth': 'bearer',
  'model': 'Meta-Llama-3.3-70B-Instruct'
 },
 'deepinfra': {
  'url': 'https://api.deepinfra.com/v1/openai/chat/completions',
  'key_env': 'DEEPINFRA_API_KEY',
  'auth': 'bearer',
  'model': 'meta-llama/Llama-3.3-70B-Instruct'
 },
 'novita': {
  'url': 'https://api.novita.ai/v3/openai/chat/completions',
  'key_env': 'NOVITA_API_KEY',
  'auth': 'bearer',
  'model': 'meta-llama/llama-3.3-70b-instruct'
 },
 'hyperbolic': {
  'url': 'https://api.hyperbolic.xyz/v1/chat/completions',
  'key_env': 'HYPERBOLIC_API_KEY',
  'auth': 'bearer',
  'model': 'meta-llama/Llama-3.3-70B-Instruct'
 },
}

def get_active_brains():
 active = []
 for name, cfg in BRAIN_CONFIGS.items():
  key = os.environ.get(cfg['key_env'], '')
  if key and len(key) > 5 and 'DISABLED' not in cfg['key_env']:
   active.append((name, cfg, key))
 return active

def ask_brain(name, cfg, key, prompt, max_tokens=2000):
 try:
  if cfg['auth'] == 'query':
   url = cfg['url'] + '?key=' + key
   body = json.dumps({
    'contents': [{'parts': [{'text': prompt}]}],
    'generationConfig': {'maxOutputTokens': max_tokens}
   }).encode()
   req = urllib.request.Request(url, data=body, method='POST')
   req.add_header('Content-Type', 'application/json')
  else:
   url = cfg['url']
   payload = {
    'messages': [{'role': 'user', 'content': prompt}],
    'max_tokens': max_tokens,
    'temperature': 0.7
   }
   if cfg['model']:
    payload['model'] = cfg['model']
   body = json.dumps(payload).encode()
   req = urllib.request.Request(url, data=body, method='POST')
   req.add_header('Content-Type', 'application/json')
   req.add_header('Authorization', f'Bearer {key}')
  resp = urllib.request.urlopen(req, timeout=30, context=CTX)
  data = json.loads(resp.read().decode())
  if cfg['auth'] == 'query':
   text = data.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', '')
  else:
   text = data.get('choices', [{}])[0].get('message', {}).get('content', '')
  return text.strip() if text else None
 except Exception as e:
  print(f"[BRAIN] {name} error: {e}")
  return None

def ask_collective(prompt, max_tokens=2000):
 brains = get_active_brains()
 random.shuffle(brains)
 for name, cfg, key in brains[:3]:
  result = ask_brain(name, cfg, key, prompt, max_tokens)
  if result:
   return {'brain': name, 'response': result}
 return None
# ============================================================
# UTILITY: Safe JSON load/save
# ============================================================
def safe_load(path, default=None):
 if default is None:
  default = {}
 try:
  if os.path.exists(path):
   with open(path, 'r') as f:
    return json.load(f)
 except Exception as e:
  print(f"[IO] Error loading {path}: {e}")
 return default

def safe_save(path, data):
 try:
  tmp = path + '.tmp'
  with open(tmp, 'w') as f:
   json.dump(data, f, indent=1, default=str)
  os.replace(tmp, path)
 except Exception as e:
  print(f"[IO] Error saving {path}: {e}")

# ============================================================
# MODULE 1: GITHUB AUTO-DEPLOY
# ============================================================
class GitHubDeployer:
 def __init__(self):
  self.token = GITHUB_TOKEN
  self.repo = GITHUB_REPO
  self.log = safe_load(ACTION_LOG_PATH, {'pushes': [], 'total_pushes': 0})

 def _api_call(self, endpoint, method='GET', data=None):
  url = f"{GITHUB_API}/repos/{self.repo}/{endpoint}"
  body = json.dumps(data).encode() if data else None
  req = urllib.request.Request(url, data=body, method=method)
  req.add_header('Authorization', f'token {self.token}')
  req.add_header('Accept', 'application/vnd.github.v3+json')
  req.add_header('User-Agent', 'ZenithActionDispatcher')
  if data:
   req.add_header('Content-Type', 'application/json')
  try:
   resp = urllib.request.urlopen(req, timeout=30, context=CTX)
   return json.loads(resp.read().decode())
  except urllib.error.HTTPError as e:
   err_body = e.read().decode() if e.fp else ''
   print(f"[GH] API error {e.code}: {err_body[:200]}")
   return None
  except Exception as e:
   print(f"[GH] Request error: {e}")
   return None

 def get_file(self, path):
  return self._api_call(f"contents/{path}")

 def push_file(self, path, content, message):
  existing = self.get_file(path)
  encoded = base64.b64encode(content.encode()).decode()
  payload = {
   'message': message,
   'content': encoded,
   'committer': {
    'name': 'Zenith AGI',
    'email': 'zenith@tcc-sovereignty.ai'
   }
  }
  if existing and isinstance(existing, dict) and existing.get('sha'):
   payload['sha'] = existing['sha']
  result = self._api_call(f"contents/{path}", method='PUT', data=payload)
  if result and result.get('content'):
   entry = {
    'time': datetime.now().isoformat(),
    'path': path,
    'size': len(content),
    'sha': result['content'].get('sha', ''),
    'message': message,
    'status': 'success'
   }
   self.log['pushes'].append(entry)
   self.log['total_pushes'] = self.log.get('total_pushes', 0) + 1
   if len(self.log['pushes']) > 500:
    self.log['pushes'] = self.log['pushes'][-500:]
   safe_save(ACTION_LOG_PATH, self.log)
   print(f"[GH] Pushed {path} ({len(content)} bytes) - {message}")
   return True
  else:
   entry = {
    'time': datetime.now().isoformat(),
    'path': path,
    'size': len(content),
    'message': message,
    'status': 'failed'
   }
   self.log['pushes'].append(entry)
   safe_save(ACTION_LOG_PATH, self.log)
   print(f"[GH] FAILED to push {path}")
   return False

 def create_file(self, path, content, message):
  return self.push_file(path, content, message)

 def process_deploy_action(self, action):
  path = action.get('path', '')
  content = action.get('content', '')
  message = action.get('message', f"Auto-deploy: {path}")
  if not path or not content:
   return {'status': 'failed', 'error': 'Missing path or content'}
  success = self.push_file(path, content, message)
  return {'status': 'success' if success else 'failed', 'path': path, 'size': len(content)}

# ============================================================
# MODULE 2: ACTION QUEUE SYSTEM
# ============================================================
class ActionQueue:
 def __init__(self):
  self.queue = safe_load(ACTION_QUEUE_PATH, {'actions': [], 'processed': 0})
  self.results = safe_load(ACTION_RESULTS_PATH, {'results': [], 'total': 0})

 def get_pending(self):
  actions = self.queue.get('actions', [])
  return sorted(
   [a for a in actions if a.get('status') == 'pending'],
   key=lambda x: x.get('priority', 0),
   reverse=True
  )

 def mark_done(self, action_id, result):
  for a in self.queue.get('actions', []):
   if a.get('id') == action_id:
    a['status'] = 'completed'
    a['completed_at'] = datetime.now().isoformat()
    a['result'] = result
    break
  self.queue['processed'] = self.queue.get('processed', 0) + 1
  safe_save(ACTION_QUEUE_PATH, self.queue)
  self.results['results'].append({
   'id': action_id,
   'time': datetime.now().isoformat(),
   'result': result
  })
  self.results['total'] = self.results.get('total', 0) + 1
  if len(self.results['results']) > 1000:
   self.results['results'] = self.results['results'][-1000:]
  safe_save(ACTION_RESULTS_PATH, self.results)

 def mark_failed(self, action_id, error):
  for a in self.queue.get('actions', []):
   if a.get('id') == action_id:
    a['status'] = 'failed'
    a['failed_at'] = datetime.now().isoformat()
    a['error'] = str(error)[:500]
    break
  safe_save(ACTION_QUEUE_PATH, self.queue)
  self.results['results'].append({
   'id': action_id,
   'time': datetime.now().isoformat(),
   'result': {'status': 'failed', 'error': str(error)[:500]}
  })
  self.results['total'] = self.results.get('total', 0) + 1
  safe_save(ACTION_RESULTS_PATH, self.results)

 def reload(self):
  self.queue = safe_load(ACTION_QUEUE_PATH, {'actions': [], 'processed': 0})
# ============================================================
# MODULE 3: CONTENT ENGINE
# ============================================================
class ContentEngine:
 def __init__(self):
  self.generated_count = 0

 def _get_hot_topics(self):
  kb = safe_load(KB_PATH, {})
  topics = []
  for source, entries in kb.items():
   if isinstance(entries, list):
    for entry in entries[-10:]:
     if isinstance(entry, dict):
      title = entry.get('title', entry.get('topic', entry.get('question', '')))
      if title:
       topics.append({'source': source, 'title': title, 'data': entry})
   elif isinstance(entries, dict):
    for key, val in list(entries.items())[-5:]:
     topics.append({'source': source, 'title': str(key), 'data': val})
  random.shuffle(topics)
  return topics[:20]

 def generate_blog_post(self, topic):
  prompt = "Write a compelling blog post about: " + topic['title'] + "\n"
  prompt += "Source: " + topic['source'] + "\n"
  prompt += "Requirements: Engaging title, 3-5 paragraphs, key insights, professional tone.\n"
  prompt += 'Format as JSON: {"title": "...", "body": "...", "tags": ["tag1"], "source": "..."}'
  result = ask_collective(prompt, max_tokens=1500)
  if result and result.get('response'):
   try:
    text = result['response']
    start = text.find('{')
    end = text.rfind('}') + 1
    if start >= 0 and end > start:
     post = json.loads(text[start:end])
     post['generated_by'] = result['brain']
     post['generated_at'] = datetime.now().isoformat()
     post['source_topic'] = topic['title']
     fname = "blog_" + datetime.now().strftime('%Y%m%d_%H%M%S') + ".json"
     fpath = os.path.join(CONTENT_DIR, 'blog', fname)
     safe_save(fpath, post)
     self.generated_count += 1
     print(f"[CONTENT] Blog post: {post.get('title', 'untitled')[:60]}")
     return post
   except json.JSONDecodeError:
    body_text = result['response']
    post = {
     'title': topic['title'], 'body': body_text,
     'tags': [topic['source']], 'source': topic['source'],
     'generated_by': result['brain'],
     'generated_at': datetime.now().isoformat()
    }
    fname = "blog_" + datetime.now().strftime('%Y%m%d_%H%M%S') + ".json"
    fpath = os.path.join(CONTENT_DIR, 'blog', fname)
    safe_save(fpath, post)
    self.generated_count += 1
    return post
  return None
 def generate_tweet_thread(self, topic):
  prompt = "Create a tweet thread (5-7 tweets) about: " + topic['title'] + "\n"
  prompt += "Requirements: First tweet hooks reader, each under 280 chars, relevant hashtags.\n"
  prompt += 'Format as JSON: {"thread": ["tweet1", "tweet2"], "hashtags": ["#tag1"], "source": "..."}'
  result = ask_collective(prompt, max_tokens=1000)
  if result and result.get('response'):
   try:
    text = result['response']
    start = text.find('{')
    end = text.rfind('}') + 1
    if start >= 0 and end > start:
     thread = json.loads(text[start:end])
     thread['generated_by'] = result['brain']
     thread['generated_at'] = datetime.now().isoformat()
     fname = "tweets_" + datetime.now().strftime('%Y%m%d_%H%M%S') + ".json"
     fpath = os.path.join(CONTENT_DIR, 'tweets', fname)
     safe_save(fpath, thread)
     self.generated_count += 1
     print(f"[CONTENT] Tweet thread: {len(thread.get('thread', []))} tweets")
     return thread
   except json.JSONDecodeError:
    pass
  return None

 def generate_article_summary(self, topic):
  prompt = "Write a concise article summary about: " + topic['title'] + "\n"
  prompt += "Requirements: 2-3 paragraph executive summary, key takeaways, relevance to crypto/tech.\n"
  prompt += 'Format as JSON: {"title": "...", "summary": "...", "takeaways": ["point1"], "relevance": "..."}'
  result = ask_collective(prompt, max_tokens=1000)
  if result and result.get('response'):
   try:
    text = result['response']
    start = text.find('{')
    end = text.rfind('}') + 1
    if start >= 0 and end > start:
     article = json.loads(text[start:end])
     article['generated_by'] = result['brain']
     article['generated_at'] = datetime.now().isoformat()
     fname = "article_" + datetime.now().strftime('%Y%m%d_%H%M%S') + ".json"
     fpath = os.path.join(CONTENT_DIR, 'articles', fname)
     safe_save(fpath, article)
     self.generated_count += 1
     print(f"[CONTENT] Article: {article.get('title', 'untitled')[:60]}")
     return article
   except json.JSONDecodeError:
    pass
  return None

 def run_cycle(self):
  topics = self._get_hot_topics()
  if not topics:
   print("[CONTENT] No hot topics found in knowledge base")
   return None
  topic = topics[0]
  roll = random.randint(1, 3)
  if roll == 1:
   return self.generate_blog_post(topic)
  elif roll == 2:
   return self.generate_tweet_thread(topic)
  else:
   return self.generate_article_summary(topic)
# ============================================================
# MODULE 4: CRYPTO INTELLIGENCE
# ============================================================
class CryptoIntelligence:
 def __init__(self):
  self.signals = safe_load(CRYPTO_SIGNALS_PATH, {
   'signals': [], 'accuracy': {'correct': 0, 'total': 0},
   'last_update': None
  })
  self.coins = ['bitcoin', 'ethereum', 'solana', 'dogecoin', 'cardano',
                'polkadot', 'avalanche-2', 'chainlink', 'matic-network', 'near',
                'sui', 'aptos', 'arbitrum', 'optimism', 'celestia',
                'jupiter-exchange-solana', 'bonk', 'pepe', 'dogwifcoin', 'render-token']

 def fetch_prices(self):
  ids = ','.join(self.coins)
  url = "https://api.coingecko.com/api/v3/simple/price?ids=" + ids
  url += "&vs_currencies=usd&include_24hr_change=true&include_24hr_vol=true"
  try:
   req = urllib.request.Request(url)
   req.add_header('User-Agent', 'ZenithCrypto/1.0')
   resp = urllib.request.urlopen(req, timeout=15, context=CTX)
   return json.loads(resp.read().decode())
  except Exception as e:
   print(f"[CRYPTO] Price fetch error: {e}")
   return {}

 def calculate_signals(self, prices):
  signals = []
  for coin, data in prices.items():
   if not isinstance(data, dict):
    continue
   price = data.get('usd', 0)
   change_24h = data.get('usd_24h_change', 0)
   vol = data.get('usd_24h_vol', 0)
   if price <= 0:
    continue
   signal = 'HOLD'
   confidence = 50
   reasoning = []
   if change_24h > 10:
    signal = 'SELL'
    confidence = 70
    reasoning.append(f"Major pump +{change_24h:.1f}% - potential correction")
   elif change_24h > 5:
    signal = 'HOLD'
    confidence = 55
    reasoning.append(f"Moderate gain +{change_24h:.1f}% - watch for continuation")
   elif change_24h < -10:
    signal = 'BUY'
    confidence = 65
    reasoning.append(f"Major dip {change_24h:.1f}% - potential recovery play")
   elif change_24h < -5:
    signal = 'BUY'
    confidence = 55
    reasoning.append(f"Dip {change_24h:.1f}% - possible entry point")
   if vol and vol > 1000000000:
    confidence += 10
    reasoning.append("High volume confirms move")
   signals.append({
    'coin': coin, 'price': price,
    'change_24h': round(change_24h, 2) if change_24h else 0,
    'volume_24h': vol, 'signal': signal,
    'confidence': min(confidence, 95),
    'reasoning': reasoning,
    'timestamp': datetime.now().isoformat()
   })
  return sorted(signals, key=lambda x: abs(x.get('change_24h', 0)), reverse=True)

 def get_brain_analysis(self, top_movers):
  if not top_movers:
   return None
  summary = "Analyze these crypto moves and give trading insights:\n"
  for m in top_movers[:5]:
   summary += "- " + m['coin'].upper() + ": $" + str(round(m['price'], 4))
   summary += ", " + str(round(m['change_24h'], 1)) + "% 24h\n"
  summary += "\nFor each: Buy, sell, or hold? Why? Likely next move?"
  result = ask_collective(summary, max_tokens=1000)
  return result

 def check_alerts(self, signals):
  alerts = []
  for sig in signals:
   change = abs(sig.get('change_24h', 0))
   if change > 10:
    alerts.append({
     'coin': sig['coin'], 'type': 'MAJOR_MOVE',
     'change': sig['change_24h'], 'price': sig['price'],
     'signal': sig['signal'], 'time': datetime.now().isoformat()
    })
  return alerts

 def run_cycle(self):
  prices = self.fetch_prices()
  if not prices:
   print("[CRYPTO] No price data available")
   return []
  signals = self.calculate_signals(prices)
  top_movers = signals[:5]
  analysis = self.get_brain_analysis(top_movers)
  if analysis:
   for sig in signals:
    sig['brain_analysis'] = analysis.get('brain', 'unknown')
  alerts = self.check_alerts(signals)
  if alerts:
   print(f"[CRYPTO] ALERTS: {len(alerts)} major moves detected!")
   for a in alerts:
    print(f"  >> {a['coin'].upper()} {a['change']:+.1f}% at ${a['price']}")
  self.signals['signals'] = signals
  self.signals['last_update'] = datetime.now().isoformat()
  self.signals['alerts'] = alerts
  if analysis:
   self.signals['brain_analysis'] = analysis.get('response', '')[:2000]
  safe_save(CRYPTO_SIGNALS_PATH, self.signals)
  print(f"[CRYPTO] Updated {len(signals)} signals, {len(alerts)} alerts")
  return signals
# ============================================================
# MODULE 5: COMMANDER REPORTS
# ============================================================
class CommanderReports:
 def __init__(self):
  self.last_report_time = None

 def should_generate(self):
  if self.last_report_time is None:
   return True
  elapsed = (datetime.now() - self.last_report_time).total_seconds()
  return elapsed >= 3600

 def generate_report(self, cycle_count, crypto_signals, content_count, action_count):
  kb = safe_load(KB_PATH, {})
  kb_size = sum(len(v) if isinstance(v, list) else len(v) if isinstance(v, dict) else 0 for v in kb.values())
  queue = safe_load(ACTION_QUEUE_PATH, {})
  pending = len([a for a in queue.get('actions', []) if a.get('status') == 'pending'])
  completed = len([a for a in queue.get('actions', []) if a.get('status') == 'completed'])
  action_log = safe_load(ACTION_LOG_PATH, {})
  total_pushes = action_log.get('total_pushes', 0)
  signals_data = safe_load(CRYPTO_SIGNALS_PATH, {})
  active_signals = len(signals_data.get('signals', []))
  alert_count = len(signals_data.get('alerts', []))
  brains = get_active_brains()
  api_reg = safe_load(API_REGISTRY_PATH, {})
  apis_known = len(api_reg.get('apis', []))
  apis_working = len([a for a in api_reg.get('apis', []) if a.get('status') == 'working'])
  report = {
   'timestamp': datetime.now().isoformat(),
   'cycle_count': cycle_count,
   'status': 'OPERATIONAL',
   'knowledge_base': {
    'total_entries': kb_size,
    'sources': len(kb)
   },
   'brain_collective': {
    'active_brains': len(brains),
    'brain_names': [b[0] for b in brains]
   },
   'action_queue': {
    'pending': pending,
    'completed': completed,
    'total_actions': action_count
   },
   'github_deploys': {
    'total_pushes': total_pushes
   },
   'crypto_intel': {
    'signals_tracked': active_signals,
    'active_alerts': alert_count
   },
   'content_engine': {
    'pieces_generated': content_count
   },
   'api_hunter': {
    'apis_known': apis_known,
    'apis_working': apis_working
   }
  }
  fname = "report_" + datetime.now().strftime('%Y%m%d_%H%M%S') + ".json"
  fpath = os.path.join(REPORTS_DIR, fname)
  safe_save(fpath, report)
  safe_save(COMMANDER_BRIEFING_PATH, report)
  self.last_report_time = datetime.now()
  print(f"[REPORT] Commander briefing generated - {kb_size} KB entries, {len(brains)} brains, {pending} pending actions")
  return report

# ============================================================
# MODULE 6: API HUNTER
# ============================================================
FREE_APIS = [
 {"url": "https://api.publicapis.org/entries?category=Science", "category": "science", "name": "Public APIs - Science"},
 {"url": "https://api.github.com/trending", "category": "tech", "name": "GitHub Trending"},
 {"url": "https://hacker-news.firebaseio.com/v0/topstories.json", "category": "tech", "name": "HackerNews Top"},
 {"url": "https://api.coingecko.com/api/v3/search/trending", "category": "crypto", "name": "CoinGecko Trending"},
 {"url": "https://newsapi.org/v2/top-headlines?country=us&apiKey=demo", "category": "news", "name": "NewsAPI Headlines"},
 {"url": "https://api.spacexdata.com/v4/launches/latest", "category": "space", "name": "SpaceX Latest"},
 {"url": "https://api.nasa.gov/planetary/apod?api_key=DEMO_KEY", "category": "space", "name": "NASA APOD"},
 {"url": "https://api.adviceslip.com/advice", "category": "misc", "name": "Advice Slip"},
 {"url": "https://api.quotable.io/random", "category": "misc", "name": "Random Quote"},
 {"url": "https://dog.ceo/api/breeds/list/all", "category": "misc", "name": "Dog Breeds"},
 {"url": "https://catfact.ninja/fact", "category": "misc", "name": "Cat Facts"},
 {"url": "https://official-joke-api.appspot.com/random_joke", "category": "misc", "name": "Random Joke"},
 {"url": "https://api.open-meteo.com/v1/forecast?latitude=34.05&longitude=-118.24&current_weather=true", "category": "weather", "name": "Open-Meteo LA"},
 {"url": "https://earthquake.usgs.gov/fdsnws/event/1/query?format=geojson&limit=5&orderby=time", "category": "science", "name": "USGS Earthquakes"},
 {"url": "https://api.exchangerate-api.com/v4/latest/USD", "category": "finance", "name": "Exchange Rates"},
 {"url": "https://api.ipify.org?format=json", "category": "network", "name": "My IP"},
 {"url": "https://worldtimeapi.org/api/timezone/America/Los_Angeles", "category": "time", "name": "World Time LA"},
 {"url": "https://api.dictionaryapi.dev/api/v2/entries/en/sovereignty", "category": "language", "name": "Dictionary API"},
 {"url": "https://api.genderize.io?name=Amos", "category": "misc", "name": "Genderize"},
 {"url": "https://api.agify.io?name=Jeremy", "category": "misc", "name": "Agify"},
 {"url": "https://randomuser.me/api/", "category": "misc", "name": "Random User"},
 {"url": "https://api.chucknorris.io/jokes/random", "category": "misc", "name": "Chuck Norris"},
 {"url": "https://www.boredapi.com/api/activity", "category": "misc", "name": "Bored API"},
 {"url": "https://api.coinpaprika.com/v1/tickers", "category": "crypto", "name": "CoinPaprika Tickers"},
 {"url": "https://api.alternative.me/fng/?limit=1", "category": "crypto", "name": "Crypto Fear&Greed"},
]

class APIHunter:
 def __init__(self):
  self.registry = safe_load(API_REGISTRY_PATH, {'apis': [], 'tested': 0, 'working': 0})

 def get_untested(self):
  tested_urls = set(a.get('url', '') for a in self.registry.get('apis', []))
  return [api for api in FREE_APIS if api['url'] not in tested_urls]

 def test_api(self, api_info):
  url = api_info['url']
  try:
   req = urllib.request.Request(url)
   req.add_header('User-Agent', 'ZenithAPIHunter/1.0')
   start = time.time()
   resp = urllib.request.urlopen(req, timeout=10, context=CTX)
   elapsed = time.time() - start
   data = resp.read().decode()[:5000]
   try:
    parsed = json.loads(data)
    data_quality = 'structured'
   except json.JSONDecodeError:
    data_quality = 'text' if len(data) > 100 else 'minimal'
   entry = {
    'url': url, 'name': api_info.get('name', url),
    'category': api_info.get('category', 'unknown'),
    'status': 'working', 'last_tested': datetime.now().isoformat(),
    'response_time_ms': round(elapsed * 1000),
    'data_quality': data_quality,
    'data_sample': data[:200]
   }
   self.registry['apis'].append(entry)
   self.registry['tested'] = self.registry.get('tested', 0) + 1
   self.registry['working'] = self.registry.get('working', 0) + 1
   safe_save(API_REGISTRY_PATH, self.registry)
   print(f"[API] WORKING: {api_info.get('name', url)} ({elapsed*1000:.0f}ms, {data_quality})")
   return entry
  except Exception as e:
   entry = {
    'url': url, 'name': api_info.get('name', url),
    'category': api_info.get('category', 'unknown'),
    'status': 'failed', 'last_tested': datetime.now().isoformat(),
    'error': str(e)[:200]
   }
   self.registry['apis'].append(entry)
   self.registry['tested'] = self.registry.get('tested', 0) + 1
   safe_save(API_REGISTRY_PATH, self.registry)
   print(f"[API] FAILED: {api_info.get('name', url)} - {e}")
   return entry

 def run_cycle(self):
  untested = self.get_untested()
  if not untested:
   print("[API] All APIs tested")
   return None
  target = untested[0]
  return self.test_api(target)
# ============================================================
# MAIN DISPATCHER - Orchestrates all modules
# ============================================================
class ActionDispatcher:
 def __init__(self):
  print("[DISPATCH] Initializing Universal Action Dispatcher v1.0")
  self.github = GitHubDeployer()
  self.queue = ActionQueue()
  self.content = ContentEngine()
  self.crypto = CryptoIntelligence()
  self.reports = CommanderReports()
  self.api_hunter = APIHunter()
  self.cycle_count = 0
  self.action_count = 0
  self.status = {
   'state': 'running',
   'started_at': datetime.now().isoformat(),
   'cycles': 0,
   'actions_processed': 0,
   'content_generated': 0,
   'last_cycle': None
  }
  safe_save(ACTION_STATUS_PATH, self.status)
  print("[DISPATCH] All modules initialized")

 def process_action(self, action):
  action_type = action.get('type', 'unknown')
  action_id = action.get('id', 'no-id')
  print(f"[DISPATCH] Processing action: {action_type} (id: {action_id})")
  try:
   if action_type == 'github_deploy':
    result = self.github.process_deploy_action(action)
   elif action_type == 'generate_content':
    topic = action.get('topic', '')
    ctype = action.get('content_type', 'blog')
    fake_topic = {'title': topic, 'source': 'agi_core'}
    if ctype == 'blog':
     result = self.content.generate_blog_post(fake_topic)
    elif ctype == 'tweet':
     result = self.content.generate_tweet_thread(fake_topic)
    else:
     result = self.content.generate_article_summary(fake_topic)
    result = {'status': 'success' if result else 'failed', 'output': str(result)[:500]}
   elif action_type == 'research':
    query = action.get('query', action.get('topic', ''))
    result = ask_collective(query, max_tokens=1500)
    result = {'status': 'success' if result else 'failed', 'output': str(result)[:1000]}
   elif action_type == 'crypto_analysis':
    coin = action.get('coin', 'bitcoin')
    prompt = 'Detailed analysis of ' + coin + ': price prediction, market sentiment, key levels, recommendation.'
    brain_result = ask_collective(prompt, max_tokens=1000)
    result = {'status': 'success' if brain_result else 'failed', 'analysis': str(brain_result)[:1000]}
   elif action_type == 'api_test':
    url = action.get('url', '')
    api_result = self.api_hunter.test_api({'url': url, 'name': action.get('name', url), 'category': 'custom'})
    result = {'status': api_result.get('status', 'failed')}
   else:
    result = {'status': 'unknown_type', 'type': action_type}
   self.queue.mark_done(action_id, result)
   self.action_count += 1
   print(f"[DISPATCH] Action {action_id} completed: {result.get('status', 'unknown')}")
   return result
  except Exception as e:
   self.queue.mark_failed(action_id, str(e))
   print(f"[DISPATCH] Action {action_id} FAILED: {e}")
   return {'status': 'error', 'error': str(e)}

 def run_cycle(self):
  self.cycle_count += 1
  start = time.time()
  print(f"\n{'='*60}")
  print(f"[DISPATCH] Cycle {self.cycle_count} at {datetime.now().isoformat()}")
  print(f"{'='*60}")

  # Step 1: Process action queue
  self.queue.reload()
  pending = self.queue.get_pending()
  if pending:
   action = pending[0]
   self.process_action(action)
  else:
   print("[DISPATCH] No pending actions in queue")

  # Step 2: Generate content
  try:
   content_result = self.content.run_cycle()
   if content_result:
    print(f"[DISPATCH] Content generated successfully")
  except Exception as e:
   print(f"[DISPATCH] Content engine error: {e}")

  # Step 3: Crypto intelligence
  try:
   crypto_result = self.crypto.run_cycle()
   if crypto_result:
    print(f"[DISPATCH] Crypto signals updated: {len(crypto_result)} coins")
  except Exception as e:
   print(f"[DISPATCH] Crypto intel error: {e}")

  # Step 4: API Hunter
  try:
   api_result = self.api_hunter.run_cycle()
  except Exception as e:
   print(f"[DISPATCH] API hunter error: {e}")

  # Step 5: Commander report (hourly)
  if self.reports.should_generate():
   try:
    self.reports.generate_report(
     self.cycle_count,
     len(self.crypto.signals.get('signals', [])),
     self.content.generated_count,
     self.action_count
    )
   except Exception as e:
    print(f"[DISPATCH] Report error: {e}")

  # Update status
  self.status['cycles'] = self.cycle_count
  self.status['actions_processed'] = self.action_count
  self.status['content_generated'] = self.content.generated_count
  self.status['last_cycle'] = datetime.now().isoformat()
  self.status['pending_actions'] = len(self.queue.get_pending())
  safe_save(ACTION_STATUS_PATH, self.status)

  elapsed = time.time() - start
  print(f"[DISPATCH] Cycle {self.cycle_count} complete in {elapsed:.0f}s")
  print(f"[DISPATCH] Actions: {self.action_count} | Content: {self.content.generated_count} | Next in 60s")

 def run_forever(self):
  print(f"\n{'='*60}")
  print(f"Zenith Universal Action Dispatcher v1.0")
  print(f"THE ACTION LAYER - Turns thinking into DOING")
  print(f"Modules: GitHub Deploy | Content Engine | Crypto Intel | Reports | API Hunter")
  print(f"Commander: Jeremy Pyne | Sovereign AI Project")
  print(f"{'='*60}")
  while True:
   try:
    self.run_cycle()
   except Exception as e:
    print(f"[DISPATCH] Cycle error: {e}")
   time.sleep(60)

if __name__ == "__main__":
 dispatcher = ActionDispatcher()
 dispatcher.run_forever()
