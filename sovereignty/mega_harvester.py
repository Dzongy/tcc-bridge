#!/usr/bin/env python3
"""
MegaHarvester v1.0 -- TCC Sovereignty Knowledge Engine
Pulls from ALL free sources: Wikipedia, Reddit, HN, ArXiv, CoinGecko, Groq Brain
Stores everything in sovereignty/knowledge_base.json
Zenith becomes a god.
"""

import os
import sys
import json
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

# Load .env from parent dir
from dotenv import load_dotenv
env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '.env')
load_dotenv(env_path)

# Import brain router
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from brain_router import BrainRouter

try:
 import requests
except ImportError:
 print('[MEGA] ERROR: pip install requests')
 sys.exit(1)

KNOWLEDGE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'knowledge_base.json')

# -------------------------------------------------------
# Wikipedia Topics -- 100+ high-value knowledge domains
# -------------------------------------------------------
WIKI_TOPICS = [
 # AI / ML
 'artificial_intelligence', 'machine_learning', 'deep_learning', 'neural_network',
 'reinforcement_learning', 'natural_language_processing', 'computer_vision',
 'generative_adversarial_network', 'transformer_(machine_learning_model)',
 'large_language_model', 'GPT-4', 'artificial_general_intelligence',
 'autonomous_agent', 'expert_system', 'knowledge_graph',
 # Crypto / DeFi
 'blockchain', 'cryptocurrency', 'bitcoin', 'ethereum', 'solana_(blockchain_platform)',
 'smart_contract', 'decentralized_finance', 'non-fungible_token', 'tokenomics',
 'liquidity_pool', 'yield_farming', 'flash_loan',
 'maximal_extractable_value', 'decentralized_exchange', 'stablecoin',
 'proof_of_stake', 'proof_of_work', 'layer_2_(blockchain)',
 # Business / Marketing
 'marketing_strategy', 'sales_funnel', 'copywriting', 'entrepreneurship',
 'venture_capital', 'passive_income', 'search_engine_optimization',
 'social_media_marketing', 'growth_hacking', 'affiliate_marketing',
 'email_marketing', 'content_marketing', 'product/market_fit',
 'minimum_viable_product', 'lean_startup', 'software_as_a_service',
 'recurring_revenue', 'dropshipping', 'arbitrage',
 # Trading
 'algorithmic_trading', 'technical_analysis', 'candlestick_pattern',
 'support_and_resistance', 'moving_average', 'relative_strength_index',
 'MACD', 'bollinger_bands', 'fibonacci_retracement', 'market_making',
 'high-frequency_trading', 'quantitative_analysis_(finance)',
 # Misc high-value
 'network_effect', 'metcalfe%27s_law', 'game_theory', 'mechanism_design',
 'zero-knowledge_proof', 'homomorphic_encryption', 'federated_learning',
 'edge_computing', 'quantum_computing', 'web3',
 # --- STRATEGIC MASTERS ---
 'Chase_Hughes', 'Robert_Cialdini', 'Sun_Tzu', 'The_Art_of_War',
 'Warren_Buffett', 'Charlie_Munger', 'Ray_Dalio', 'Elon_Musk',
 'Naval_Ravikant', 'Alex_Hormozi', 'Grant_Cardone', 'Gary_Vaynerchuk',
 'Robert_Greene', 'The_48_Laws_of_Power', 'Niccolo_Machiavelli', 'The_Prince_(Machiavelli)',
 # --- PSYCHOLOGY / INFLUENCE ---
 'Psychological_manipulation', 'Dark_psychology', 'Behavioral_economics',
 'Negotiation', 'Social_engineering_(security)', 'Cold_reading',
 'Neuro-linguistic_programming', 'Propaganda_techniques',
 'List_of_cognitive_biases', 'Persuasion', 'Power_(social_and_political)',
 'OODA_loop', 'John_Boyd_(military_strategist)',
 # --- FINANCE / INVESTING ---
 'Compound_interest', 'Hedge_fund', 'Market_psychology',
 'Fear_and_greed_index', 'Options_strategy', 'Kelly_criterion',
 'Monte_Carlo_method', 'Risk_management', 'Modern_portfolio_theory',
 'Dollar_cost_averaging', 'Angel_investor', 'Crowdfunding',
 'Revenue_model', 'Pricing_strategies',
 # --- COGNITIVE BIASES / PERSUASION SCIENCE ---
 'Loss_aversion', 'Anchoring_(cognitive_bias)', 'Scarcity_(social_psychology)',
 'Social_proof', 'Authority_bias', 'Reciprocity_(social_psychology)',
 'Framing_effect_(psychology)', 'Chris_Voss',
]

# Domain classifier for wiki topics
WIKI_DOMAIN_MAP = {
 'crypto': [
  'blockchain','cryptocurrency','bitcoin','ethereum','solana_(blockchain_platform)',
  'smart_contract','decentralized_finance','non-fungible_token','tokenomics',
  'liquidity_pool','yield_farming','flash_loan','maximal_extractable_value',
  'decentralized_exchange','stablecoin','proof_of_stake','proof_of_work',
  'layer_2_(blockchain)','zero-knowledge_proof','web3',
 ],
 'ai': [
  'artificial_intelligence','machine_learning','deep_learning','neural_network',
  'reinforcement_learning','natural_language_processing','computer_vision',
  'generative_adversarial_network','transformer_(machine_learning_model)',
  'large_language_model','GPT-4','artificial_general_intelligence',
  'autonomous_agent','expert_system','knowledge_graph','federated_learning',
  'quantum_computing','edge_computing',
 ],
 'trading': [
  'algorithmic_trading','technical_analysis','candlestick_pattern',
  'support_and_resistance','moving_average','relative_strength_index',
  'MACD','bollinger_bands','fibonacci_retracement','market_making',
  'high-frequency_trading','quantitative_analysis_(finance)',
  'Options_strategy','Kelly_criterion','Monte_Carlo_method',
  'Risk_management','Modern_portfolio_theory','Dollar_cost_averaging',
  'Market_psychology','Fear_and_greed_index',
 ],
 'psychology': [
  'Psychological_manipulation','Dark_psychology','Behavioral_economics',
  'Negotiation','Social_engineering_(security)','Cold_reading',
  'Neuro-linguistic_programming','Propaganda_techniques',
  'List_of_cognitive_biases','Persuasion','Power_(social_and_political)',
  'Loss_aversion','Anchoring_(cognitive_bias)','Scarcity_(social_psychology)',
  'Social_proof','Authority_bias','Reciprocity_(social_psychology)',
  'Framing_effect_(psychology)','Chris_Voss',
  'Robert_Cialdini','Chase_Hughes',
 ],
 'strategy': [
  'Sun_Tzu','The_Art_of_War','Robert_Greene','The_48_Laws_of_Power',
  'Niccolo_Machiavelli','The_Prince_(Machiavelli)','OODA_loop',
  'John_Boyd_(military_strategist)','game_theory','mechanism_design',
  'network_effect','metcalfe%27s_law',
 ],
 'finance': [
  'Compound_interest','Hedge_fund','Angel_investor','Crowdfunding',
  'Revenue_model','Pricing_strategies','venture_capital',
  'Warren_Buffett','Charlie_Munger','Ray_Dalio',
 ],
 'business': [
  'Elon_Musk','Naval_Ravikant','Alex_Hormozi','Grant_Cardone',
  'Gary_Vaynerchuk','marketing_strategy','sales_funnel','copywriting',
  'entrepreneurship','passive_income','search_engine_optimization',
  'social_media_marketing','growth_hacking','affiliate_marketing',
  'email_marketing','content_marketing','product/market_fit',
  'minimum_viable_product','lean_startup','software_as_a_service',
  'recurring_revenue','dropshipping','arbitrage',
 ],
}

# Invert for fast lookup
_TOPIC_DOMAIN = {}
for dom, topics in WIKI_DOMAIN_MAP.items():
 for t in topics:
  _TOPIC_DOMAIN[t] = dom

# -------------------------------------------------------
# Reddit Subreddits -- 24 high-value communities
# -------------------------------------------------------
REDDIT_SUBS = [
 'entrepreneur', 'cryptocurrency', 'artificial', 'SideProject',
 'marketing', 'passiveincome', 'startups', 'algotrading',
 'solana', 'defi', 'MachineLearning', 'freelance', 'automation',
 # --- COMMANDER ADDITIONS ---
 'wallstreetbets', 'sales', 'copywriting',
 'stoicism', 'financialindependence', 'realestateinvesting',
 'dropship', 'AffiliateMarketing', 'socialengineering',
]

# -------------------------------------------------------
# Brain Questions -- 65 strategic genius-level queries
# -------------------------------------------------------
BRAIN_QUESTIONS = [
 # Money strategies
 ("Design a complete system for generating $5000/month passive income using only AI tools and no starting capital", "money"),
 ("What are the top 5 ways to monetize an AI agent that runs 24/7 autonomously", "money"),
 ("Create a step-by-step plan to build a one-person SaaS business that reaches $10K MRR in 6 months", "money"),
 ("What are the most profitable niches for AI-powered automation services right now", "money"),
 ("How to build multiple streams of passive income using only free AI tools and APIs", "money"),
 ("Design an automated dropshipping system that uses AI for product selection and marketing", "money"),
 ("What are the best arbitrage opportunities between crypto exchanges right now", "money"),
 ("How to create and sell AI-generated digital products at scale with zero inventory", "money"),
 ("Design a lead generation machine using free tools that produces 100 qualified leads per day", "money"),
 ("What are the highest-ROI skills to learn in 2026 for maximum income potential", "money"),
 # Crypto / DeFi
 ("What are the top 5 DeFi yield farming strategies on Solana right now and how to automate them", "crypto"),
 ("What are the most undervalued sectors in crypto right now and why", "crypto"),
 ("How would you build an autonomous AI agent that manages its own crypto portfolio", "crypto"),
 ("Explain the most profitable MEV strategies on Solana and how a bot would execute them", "crypto"),
 ("What are the safest high-yield staking opportunities across all chains right now", "crypto"),
 ("Design a crypto trading bot strategy that profits in both bull and bear markets", "crypto"),
 ("What are the emerging DeFi protocols on Solana that could 10x in the next 6 months", "crypto"),
 ("How to identify and front-run new token launches on Solana for maximum profit", "crypto"),
 ("What are the best liquidity pool strategies that minimize impermanent loss", "crypto"),
 ("Design a complete on-chain analytics system for detecting whale movements early", "crypto"),
 # AI / Tech
 ("What is the most efficient architecture for a multi-agent AI system that learns from its own outputs", "ai"),
 ("How to build a self-improving AI agent that gets smarter with every interaction", "ai"),
 ("What are the most promising open-source LLM projects and how to fine-tune them for specific tasks", "ai"),
 ("Design a knowledge graph system that an AI agent can use for long-term memory", "ai"),
 ("How to build a RAG system from scratch that outperforms ChatGPT for domain-specific questions", "ai"),
 ("What are the cutting-edge techniques for making AI agents reason better and hallucinate less", "ai"),
 ("How to create an AI pipeline that converts raw data into actionable business intelligence", "ai"),
 ("Design a multi-model routing system that picks the best AI model for each task automatically", "ai"),
 ("What are the most effective prompt engineering techniques for complex reasoning tasks", "ai"),
 ("How to build an autonomous coding agent that can debug and improve its own code", "ai"),
 # Marketing / Growth
 ("Create a viral content marketing strategy that generates leads for a one-person AI consulting business", "marketing"),
 ("What are the most effective cold outreach strategies using AI personalization in 2026", "marketing"),
 ("Design a complete SEO strategy for a new SaaS product targeting enterprise customers", "marketing"),
 ("How to build an automated social media presence that grows to 100K followers in 6 months", "marketing"),
 ("What are the highest-converting email marketing sequences for B2B SaaS products", "marketing"),
 ("Design a growth hacking playbook for a bootstrapped startup with zero marketing budget", "marketing"),
 ("How to use AI to create personalized sales funnels that convert at 3x the industry average", "marketing"),
 ("What are the best strategies for building a personal brand as an AI expert", "marketing"),
 ("Design an affiliate marketing system that generates passive commissions using AI content", "marketing"),
 ("How to leverage AI for competitive analysis and market positioning", "marketing"),
 # Product / Startup
 ("Design a framework for validating startup ideas in 48 hours using only free tools", "startup"),
 ("What are the most common reasons AI startups fail and how to avoid each one", "startup"),
 ("How to build an MVP in one weekend using AI coding assistants and no-code tools", "startup"),
 ("Design a customer acquisition strategy that costs less than $1 per user", "startup"),
 ("What are the best pricing strategies for AI-powered products and services", "startup"),
 ("How to structure equity and compensation for a small AI startup team", "startup"),
 ("Design a product roadmap for an AI agent platform targeting small businesses", "startup"),
 ("What are the key metrics every AI startup should track from day one", "startup"),
 ("How to negotiate with investors and structure a seed round for maximum founder control", "startup"),
 ("Design a complete go-to-market strategy for an AI automation agency", "startup"),
 # --- COMMANDER ADDITIONS: Strategic Psychology + Influence ---
 ("What are Chase Hughes top 10 behavioral influence techniques and how to apply them in business", "psychology"),
 ("Summarize Robert Cialdini 7 principles of persuasion with real business examples", "psychology"),
 ("What would Sun Tzu Art of War look like applied to modern digital business warfare", "strategy"),
 ("How do billionaires like Warren Buffett and Ray Dalio think differently about money than everyone else", "finance"),
 ("What are the top psychological manipulation techniques used in high-ticket sales", "psychology"),
 ("Explain the CIA behavioral profiling framework and how it can be used in marketing", "psychology"),
 ("What are the 48 Laws of Power by Robert Greene summarized with modern business applications", "strategy"),
 ("How do hedge funds use market psychology to make billions", "finance"),
 ("What are the most effective dark psychology persuasion techniques for ethical business use", "psychology"),
 ("Design a complete wealth-building system using AI automation crypto and digital marketing", "money"),
 ("What are Naval Ravikant key principles on creating wealth without trading time for money", "money"),
 ("How would Alex Hormozi structure a $100M offer for an AI consulting service", "business"),
 ("What cognitive biases can be ethically exploited in marketing funnels", "psychology"),
 ("How do the world best negotiators like Chris Voss close impossible deals", "psychology"),
 ("What is the OODA loop and how to apply it to business decision-making faster than competitors", "strategy"),
]

HEADERS = {'User-Agent': 'ZenithHarvester/1.0'}


class MegaHarvester:
 """TCC Sovereignty Mega Knowledge Harvester"""

 def __init__(self):
  self.router = BrainRouter()
  self.stats = {'total': 0, 'sources': {}, 'domains': {}}
  self.knowledge = self._load_existing()
  self._existing_keys = set()
  for entry in self.knowledge:
   key = self._make_key(entry)
   if key:
    self._existing_keys.add(key)
  print(f'[MEGA] Loaded {len(self.knowledge)} existing entries')

 def _load_existing(self):
  try:
   if os.path.exists(KNOWLEDGE_FILE):
    with open(KNOWLEDGE_FILE, 'r') as f:
     data = json.load(f)
    if isinstance(data, list):
     return data
  except Exception as e:
   print(f'[MEGA] Error loading knowledge base: {e}')
  return []

 def _make_key(self, entry):
  src = entry.get('source', '')
  if src == 'wikipedia':
   return f"wiki:{entry.get('topic', '')}"
  elif src == 'reddit':
   return f"reddit:{entry.get('subreddit', '')}:{entry.get('title', '')}"
  elif src == 'hackernews':
   return f"hn:{entry.get('id', '')}"
  elif src == 'arxiv':
   return f"arxiv:{entry.get('id', '')}"
  elif src == 'coingecko':
   return f"coin:{entry.get('id', '')}"
  elif src == 'coingecko_trending':
   return f"trending:{entry.get('id', '')}"
  elif src == 'groq':
   return f"groq:{entry.get('question', '')[:80]}"
  return None

 def _save(self, entry):
  key = self._make_key(entry)
  if key and key in self._existing_keys:
   return False
  entry['harvested_at'] = datetime.now(timezone.utc).isoformat()
  self.knowledge.append(entry)
  if key:
   self._existing_keys.add(key)
  try:
   with open(KNOWLEDGE_FILE, 'w') as f:
    json.dump(self.knowledge, f, indent=1)
  except Exception as e:
   print(f'[MEGA] Save error: {e}')
  self.stats['total'] += 1
  src = entry.get('source', 'unknown')
  self.stats['sources'][src] = self.stats['sources'].get(src, 0) + 1
  dom = entry.get('domain', 'general')
  self.stats['domains'][dom] = self.stats['domains'].get(dom, 0) + 1
  return True

 # -------------------------------------------------------
 # Wikipedia
 # -------------------------------------------------------
 def harvest_wikipedia(self):
  print('[WIKI] --- Starting Wikipedia harvest ---')
  count = 0
  for topic in WIKI_TOPICS:
   try:
    url = f'https://en.wikipedia.org/api/rest_v1/page/summary/{topic}'
    r = requests.get(url, headers=HEADERS, timeout=15)
    if r.status_code == 200:
     data = r.json()
     title = data.get('title', topic)
     extract = data.get('extract', '')
     if extract:
      domain = _TOPIC_DOMAIN.get(topic, 'general')
      saved = self._save({
       'source': 'wikipedia',
       'topic': topic,
       'title': title,
       'content': extract,
       'chars': len(extract),
       'domain': domain,
      })
      if saved:
       count += 1
       print(f'[WIKI] {topic} | {len(extract)} chars | {domain}')
      else:
       print(f'[WIKI] {topic} | SKIP (exists)')
    else:
     print(f'[WIKI] {topic} | HTTP {r.status_code}')
   except Exception as e:
    print(f'[WIKI] {topic} | ERROR: {e}')
   time.sleep(2)
  print(f'[WIKI] --- Done: {count} new entries ---')

 # -------------------------------------------------------
 # Reddit
 # -------------------------------------------------------
 def harvest_reddit(self):
  print('[REDDIT] --- Starting Reddit harvest ---')
  count = 0
  for sub in REDDIT_SUBS:
   try:
    url = f'https://www.reddit.com/r/{sub}/hot.json?limit=10'
    r = requests.get(url, headers=HEADERS, timeout=15)
    if r.status_code == 200:
     data = r.json()
     posts = data.get('data', {}).get('children', [])
     sub_count = 0
     for post in posts:
      pd = post.get('data', {})
      title = pd.get('title', '')
      selftext = pd.get('selftext', '')
      score = pd.get('score', 0)
      permalink = pd.get('permalink', '')
      if not title:
       continue
      saved = self._save({
       'source': 'reddit',
       'subreddit': sub,
       'title': title,
       'content': selftext[:2000] if selftext else '',
       'score': score,
       'url': f'https://reddit.com{permalink}',
       'domain': 'general',
      })
      if saved:
       sub_count += 1
       count += 1
     print(f'[REDDIT] r/{sub} | {sub_count} new / {len(posts)} posts')
    else:
     print(f'[REDDIT] r/{sub} | HTTP {r.status_code}')
   except Exception as e:
    print(f'[REDDIT] r/{sub} | ERROR: {e}')
   time.sleep(2)
  print(f'[REDDIT] --- Done: {count} new entries ---')

 # -------------------------------------------------------
 # Hacker News
 # -------------------------------------------------------
 def harvest_hackernews(self):
  print('[HN] --- Starting Hacker News harvest ---')
  count = 0
  try:
   r = requests.get('https://hacker-news.firebaseio.com/v0/topstories.json',
    headers=HEADERS, timeout=15)
   if r.status_code != 200:
    print(f'[HN] Top stories HTTP {r.status_code}')
    return
   story_ids = r.json()[:30]
   print(f'[HN] Fetching {len(story_ids)} stories...')
   for sid in story_ids:
    try:
     sr = requests.get(f'https://hacker-news.firebaseio.com/v0/item/{sid}.json',
      headers=HEADERS, timeout=10)
     if sr.status_code == 200:
      item = sr.json()
      if not item:
       continue
      title = item.get('title', '')
      url = item.get('url', '')
      score = item.get('score', 0)
      text = item.get('text', '')
      top_comment = ''
      kids = item.get('kids', [])
      if kids:
       try:
        cr = requests.get(
         f'https://hacker-news.firebaseio.com/v0/item/{kids[0]}.json',
         headers=HEADERS, timeout=10)
        if cr.status_code == 200:
         cd = cr.json()
         top_comment = cd.get('text', '')[:500] if cd else ''
       except Exception:
        pass
      saved = self._save({
       'source': 'hackernews',
       'id': sid,
       'title': title,
       'url': url,
       'score': score,
       'text': text[:1000] if text else '',
       'top_comment': top_comment,
       'domain': 'tech',
      })
      if saved:
       count += 1
    except Exception as e:
     print(f'[HN] Item {sid} | ERROR: {e}')
    time.sleep(1)
  except Exception as e:
   print(f'[HN] ERROR: {e}')
  print(f'[HN] --- Done: {count} new stories ---')

 # -------------------------------------------------------
 # ArXiv
 # -------------------------------------------------------
 def harvest_arxiv(self):
  print('[ARXIV] --- Starting ArXiv harvest ---')
  count = 0
  try:
   url = ('http://export.arxiv.org/api/query?'
    'search_query=cat:cs.AI+OR+cat:cs.LG&sortBy=submittedDate&max_results=20')
   r = requests.get(url, headers=HEADERS, timeout=30)
   if r.status_code != 200:
    print(f'[ARXIV] HTTP {r.status_code}')
    return
   root = ET.fromstring(r.text)
   ns = {'atom': 'http://www.w3.org/2005/Atom'}
   entries = root.findall('atom:entry', ns)
   for entry in entries:
    try:
     arxiv_id_el = entry.find('atom:id', ns)
     title_el = entry.find('atom:title', ns)
     summary_el = entry.find('atom:summary', ns)
     if arxiv_id_el is None or title_el is None:
      continue
     arxiv_id = arxiv_id_el.text.strip().split('/')[-1]
     title = ' '.join(title_el.text.strip().split())
     summary = ''
     if summary_el is not None and summary_el.text:
      summary = ' '.join(summary_el.text.strip().split())
     authors = []
     for author_el in entry.findall('atom:author', ns):
      name_el = author_el.find('atom:name', ns)
      if name_el is not None and name_el.text:
       authors.append(name_el.text.strip())
     saved = self._save({
      'source': 'arxiv',
      'id': arxiv_id,
      'title': title,
      'authors': authors[:5],
      'content': summary[:3000],
      'domain': 'ai',
     })
     if saved:
      count += 1
      print(f'[ARXIV] {arxiv_id} | {title[:60]}')
     else:
      print(f'[ARXIV] {arxiv_id} | SKIP (exists)')
    except Exception as e:
     print(f'[ARXIV] Entry parse error: {e}')
  except Exception as e:
   print(f'[ARXIV] ERROR: {e}')
  print(f'[ARXIV] --- Done: {count} new papers ---')

 # -------------------------------------------------------
 # CoinGecko
 # -------------------------------------------------------
 def harvest_coingecko(self):
  print('[COIN] --- Starting CoinGecko harvest ---')
  count = 0
  try:
   url = ('https://api.coingecko.com/api/v3/coins/markets?'
    'vs_currency=usd&order=market_cap_desc&per_page=50&page=1')
   r = requests.get(url, headers=HEADERS, timeout=15)
   if r.status_code == 200:
    coins = r.json()
    for coin in coins:
     saved = self._save({
      'source': 'coingecko',
      'id': coin.get('id', ''),
      'symbol': coin.get('symbol', ''),
      'name': coin.get('name', ''),
      'price_usd': coin.get('current_price'),
      'market_cap': coin.get('market_cap'),
      'volume_24h': coin.get('total_volume'),
      'change_24h': coin.get('price_change_percentage_24h'),
      'rank': coin.get('market_cap_rank'),
      'domain': 'crypto',
     })
     if saved:
      count += 1
    print(f'[COIN] Top 50 | {count} new coins')
   else:
    print(f'[COIN] Markets HTTP {r.status_code}')
  except Exception as e:
   print(f'[COIN] Markets ERROR: {e}')
  time.sleep(2)
  try:
   r = requests.get('https://api.coingecko.com/api/v3/search/trending',
    headers=HEADERS, timeout=15)
   if r.status_code == 200:
    data = r.json()
    trending = data.get('coins', [])
    tc = 0
    for item in trending:
     coin = item.get('item', {})
     saved = self._save({
      'source': 'coingecko_trending',
      'id': coin.get('id', ''),
      'symbol': coin.get('symbol', ''),
      'name': coin.get('name', ''),
      'market_cap_rank': coin.get('market_cap_rank'),
      'domain': 'crypto',
     })
     if saved:
      tc += 1
      count += 1
    print(f'[COIN] Trending | {tc} new')
   else:
    print(f'[COIN] Trending HTTP {r.status_code}')
  except Exception as e:
   print(f'[COIN] Trending ERROR: {e}')
  print(f'[COIN] --- Done: {count} new entries ---')

 # -------------------------------------------------------
 # Brain Questions (via BrainRouter)
 # -------------------------------------------------------
 def harvest_brain_questions(self):
  print('[BRAIN] --- Starting Brain harvest ---')
  count = 0
  total = len(BRAIN_QUESTIONS)
  for i, (question, domain) in enumerate(BRAIN_QUESTIONS):
   try:
    key = f"groq:{question[:80]}"
    if key in self._existing_keys:
     print(f'[BRAIN] Q{i+1}/{total} | SKIP (exists)')
     continue
    brain_name, answer = self.router.think(question)
    if answer:
     saved = self._save({
      'source': 'groq',
      'question': question,
      'answer': answer[:5000],
      'brain_used': brain_name if brain_name else 'unknown',
      'domain': domain,
     })
     if saved:
      count += 1
      print(f'[BRAIN] Q{i+1}/{total} | {domain} | {brain_name} | {len(answer)} chars')
    else:
     print(f'[BRAIN] Q{i+1}/{total} | No answer returned')
   except Exception as e:
    print(f'[BRAIN] Q{i+1}/{total} | ERROR: {e}')
   time.sleep(3)
  print(f'[BRAIN] --- Done: {count} new answers ---')

 # -------------------------------------------------------
 # Stats
 # -------------------------------------------------------
 def print_stats(self):
  print('')
  print('=' * 60)
  print(f'  MEGA HARVESTER STATS')
  print(f'  Total entries in knowledge base: {len(self.knowledge)}')
  print(f'  New entries this cycle: {self.stats["total"]}')
  print(f'  By source: {json.dumps(self.stats["sources"])}')
  print(f'  By domain: {json.dumps(self.stats["domains"])}')
  print('=' * 60)
  print('')

 # -------------------------------------------------------
 # Run
 # -------------------------------------------------------
 def run_cycle(self):
  print('')
  print('[MEGA] ============================================')
  print(f'[MEGA] === CYCLE START === {datetime.now(timezone.utc).isoformat()}')
  print('[MEGA] ============================================')
  self.stats = {'total': 0, 'sources': {}, 'domains': {}}
  self.harvest_wikipedia()
  self.harvest_reddit()
  self.harvest_hackernews()
  self.harvest_arxiv()
  self.harvest_coingecko()
  self.harvest_brain_questions()
  self.print_stats()

 def run_forever(self):
  cycle = 0
  while True:
   cycle += 1
   print(f'[MEGA] Starting cycle {cycle}...')
   try:
    self.run_cycle()
   except Exception as e:
    print(f'[MEGA] CYCLE ERROR: {e}')
   total = len(self.knowledge)
   print(f'[MEGA] Cycle {cycle} done. {total} total entries. Sleeping 5 min...')
   time.sleep(300)


if __name__ == '__main__':
 print('[MEGA] ========================================')
 print('[MEGA]   TCC SOVEREIGNTY MEGA HARVESTER v1.0')
 print('[MEGA]   Zenith Knowledge Engine')
 print('[MEGA] ========================================')
 MegaHarvester().run_forever()
  