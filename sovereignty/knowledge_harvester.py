#!/usr/bin/env python3
"""
TCC Sovereignty -- Knowledge Harvester v1.0
24/7 brain farming via BrainRouter round-robin.
Stores results in Supabase zenith_knowledge table
with local JSON fallback.
"""

import os
import sys
import json
import time
import random
import datetime
import requests
from pathlib import Path
from dotenv import load_dotenv

# -- Load .env from parent directory (same pattern as zenith_core.py)
env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env")
load_dotenv(env_path)

# -- Import BrainRouter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from brain_router import BrainRouter

# -- Supabase config
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://vbqbbziqleymxcyesmky.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")
SUPABASE_TABLE = "zenith_knowledge"
SUPABASE_ENDPOINT = f"{SUPABASE_URL}/rest/v1/{SUPABASE_TABLE}"

# -- Local fallback path
FALLBACK_PATH = os.path.expanduser("~/tcc-bridge/sovereignty/knowledge_base.json")

# -- Rate limit delay (seconds)
REQUEST_DELAY = 3

# -- Stats tracking
stats = {
 "total": 0,
 "by_domain": {},
 "by_provider": {},
 "errors": 0,
 "supabase_ok": 0,
 "fallback_ok": 0,
}


# =========================================================
# KNOWLEDGE DOMAINS -- 5 domains, 20+ questions each
# =========================================================

DOMAINS = {
 "AI Technology & Trends": [
  "What are the most significant advances in large language models in the past year?",
  "How do mixture-of-experts architectures improve LLM efficiency?",
  "What are the best open-source LLM alternatives to GPT-4 for production use?",
  "Explain the difference between fine-tuning, RLHF, and DPO training methods.",
  "What are the current best practices for deploying LLMs on consumer hardware?",
  "How does retrieval-augmented generation (RAG) work and when should you use it?",
  "What are the key differences between transformer and state-space model architectures?",
  "What emerging AI tools are most useful for solo developers and small teams?",
  "How do AI agents differ from simple chatbots, and what makes them effective?",
  "What is the current state of multimodal AI models that handle text, image, and audio?",
  "Explain quantization methods (GPTQ, GGUF, AWQ) and their tradeoffs for local inference.",
  "What are the best strategies for prompt engineering complex multi-step tasks?",
  "How do knowledge graphs enhance AI reasoning capabilities?",
  "What are the privacy implications of running AI models locally vs cloud APIs?",
  "How does speculative decoding speed up LLM inference?",
  "What are the most promising approaches to reducing AI hallucinations?",
  "Explain how LoRA and QLoRA enable efficient fine-tuning on limited hardware.",
  "What are the best vector databases for production RAG systems in 2026?",
  "How do autonomous AI agents handle planning and tool use?",
  "What are the key trends in AI hardware (GPUs, TPUs, custom silicon) for 2026?",
  "How can small teams build competitive AI products without massive compute budgets?",
  "What is the role of synthetic data in training modern AI models?",
 ],

 "Digital Marketing & Sales": [
  "What are the most effective copywriting frameworks for high-converting sales pages?",
  "How do you build a sales funnel that converts cold traffic into buyers?",
  "What are the best strategies for growing a social media following from zero in 2026?",
  "Explain the psychology behind email sequences that drive purchases.",
  "What are the top SEO strategies for ranking content in AI-powered search results?",
  "How do you create a content strategy that builds authority and drives organic traffic?",
  "What are the most effective paid advertising strategies for small budgets under $500/month?",
  "How do you write compelling hooks for short-form video content?",
  "What is the AIDA framework and how do you apply it to digital marketing?",
  "How do you build and monetize an email list from scratch?",
  "What are the best tools and platforms for marketing automation in 2026?",
  "How do you use storytelling to sell products and services online?",
  "What are the key metrics to track for a direct-to-consumer e-commerce business?",
  "How do you optimize landing pages for maximum conversion rates?",
  "What are the best strategies for launching a product with no existing audience?",
  "How do influencer partnerships work and what makes them effective?",
  "What are the most common mistakes in digital marketing and how to avoid them?",
  "How do you create viral content consistently across platforms?",
  "What is the role of community building in modern marketing strategies?",
  "How do you use AI tools to scale content creation without losing quality?",
  "What are the best retention strategies to reduce customer churn?",
 ],

 "Crypto Trading": [
  "What are the most reliable technical analysis indicators for crypto trading?",
  "How do you identify and trade memecoin pumps safely?",
  "Explain the key DeFi protocols on Solana and how to earn yield from them.",
  "What are the best risk management strategies for crypto day trading?",
  "How do you read and interpret order book depth for crypto markets?",
  "What are the most important on-chain metrics for predicting price movements?",
  "How does the Solana ecosystem differ from Ethereum for DeFi and NFTs?",
  "What are the key patterns for identifying crypto market tops and bottoms?",
  "How do automated trading bots work and what are the best strategies for them?",
  "What are the tax implications of crypto trading in the United States?",
  "How do you evaluate a new token or project before investing?",
  "What are the best strategies for portfolio allocation across major and small-cap crypto?",
  "How do liquidity pools work and what are the risks of impermanent loss?",
  "What are the most common crypto trading mistakes and how to avoid them?",
  "How do you use RSI, MACD, and Bollinger Bands together for trade signals?",
  "What are the key differences between spot trading, futures, and options in crypto?",
  "How do whale wallets influence crypto price action and how to track them?",
  "What are the best DEX aggregators and why do they matter for trading efficiency?",
  "How do you build a systematic crypto trading strategy with backtesting?",
  "What are the emerging trends in Solana DeFi and token launches for 2026?",
  "How do you identify and avoid rug pulls and scam tokens?",
 ],

 "Product Development & Innovation": [
  "What is the lean startup methodology and how do you build an effective MVP?",
  "How do you conduct user research to validate product ideas before building?",
  "What are the best frameworks for prioritizing features in a product backlog?",
  "How do you design a product launch strategy that generates buzz and early traction?",
  "What are the key principles of iterative product development?",
  "How do you measure product-market fit and what signals indicate you have achieved it?",
  "What are the best tools for rapid prototyping and wireframing in 2026?",
  "How do you build products as a solo founder or very small team?",
  "What are the most effective user onboarding patterns for SaaS products?",
  "How do you gather and act on user feedback to improve your product?",
  "What are the key differences between B2B and B2C product development?",
  "How do you build and manage a product roadmap that balances vision and user needs?",
  "What are the best strategies for reducing time-to-market for new features?",
  "How do you use data analytics to drive product decisions?",
  "What are the most successful product-led growth strategies?",
  "How do you build products that create strong user habits and daily engagement?",
  "What are the key principles of designing APIs that developers love to use?",
  "How do you handle technical debt while maintaining development velocity?",
  "What are the best approaches to building AI-powered product features?",
  "How do you create a culture of experimentation and rapid iteration?",
  "What makes a great developer experience and why does it matter for product adoption?",
 ],

 "Business & Revenue": [
  "What are the most effective monetization strategies for digital products?",
  "How do you price a SaaS product for maximum revenue and adoption?",
  "What are the best passive income models for developers and creators?",
  "How do you scale a one-person business to six figures?",
  "What are the key metrics every bootstrapped founder should track?",
  "How do you build recurring revenue streams that grow over time?",
  "What are the best automation tools for reducing operational overhead?",
  "How do you identify and validate a profitable niche market?",
  "What are the most effective strategies for raising prices without losing customers?",
  "How do you build strategic partnerships that drive mutual growth?",
  "What are the best business models for AI-powered products and services?",
  "How do you create and sell digital courses or info products profitably?",
  "What are the key legal and tax considerations for online businesses?",
  "How do you build a personal brand that attracts clients and opportunities?",
  "What are the most common reasons startups fail and how to avoid them?",
  "How do you negotiate contracts and deals effectively as a small business?",
  "What are the best strategies for expanding into international markets?",
  "How do you build systems and processes that let you scale without burnout?",
  "What are the most effective customer acquisition channels for bootstrapped companies?",
  "How do you create a competitive moat for your business?",
  "What are the best frameworks for making strategic business decisions under uncertainty?",
 ],
}


# =========================================================
# SUPABASE STORAGE
# =========================================================

def store_supabase(topic, question, provider, response_text):
 """Store a knowledge entry in Supabase zenith_knowledge table."""
 if not SUPABASE_KEY:
  print("[WARN] No SUPABASE_SERVICE_KEY in .env -- using fallback only")
  return False
 headers = {
  "apikey": SUPABASE_KEY,
  "Authorization": f"Bearer {SUPABASE_KEY}",
  "Content-Type": "application/json",
  "Prefer": "return=minimal",
 }
 payload = {
  "topic": topic,
  "question": question,
  "provider": provider,
  "response": response_text,
  "created_at": datetime.datetime.utcnow().isoformat() + "Z",
 }
 try:
  resp = requests.post(SUPABASE_ENDPOINT, json=payload, headers=headers, timeout=15)
  if resp.status_code in (200, 201):
   stats["supabase_ok"] += 1
   return True
  elif resp.status_code == 404:
   # Table does not exist -- fall through to fallback
   print(f"[WARN] Supabase table {SUPABASE_TABLE} not found (404). Using fallback.")
   return False
  else:
   print(f"[WARN] Supabase POST returned {resp.status_code}: {resp.text[:200]}")
   return False
 except Exception as e:
  print(f"[ERROR] Supabase POST failed: {e}")
  return False


def store_fallback(topic, question, provider, response_text):
 """Append knowledge entry to local JSON file as fallback."""
 entry = {
  "topic": topic,
  "question": question,
  "provider": provider,
  "response": response_text,
  "created_at": datetime.datetime.utcnow().isoformat() + "Z",
 }
 try:
  # Ensure directory exists
  Path(FALLBACK_PATH).parent.mkdir(parents=True, exist_ok=True)
  # Load existing data or start fresh
  if os.path.exists(FALLBACK_PATH):
   with open(FALLBACK_PATH, "r", encoding="utf-8") as f:
    data = json.load(f)
  else:
   data = []
  data.append(entry)
  with open(FALLBACK_PATH, "w", encoding="utf-8") as f:
   json.dump(data, f, indent=1, ensure_ascii=True)
  stats["fallback_ok"] += 1
  return True
 except Exception as e:
  print(f"[ERROR] Fallback write failed: {e}")
  return False


def store_knowledge(topic, question, provider, response_text):
 """Try Supabase first, fallback to local JSON."""
 ok = store_supabase(topic, question, provider, response_text)
 if not ok:
  ok = store_fallback(topic, question, provider, response_text)
 return ok


# =========================================================
# FOLLOW-UP QUESTION GENERATOR
# =========================================================

def generate_followups(router, domain, existing_questions):
 """Use a brain to generate new follow-up questions for a domain."""
 prompt = (
  f"You are a knowledge curator. Given the domain '{domain}', "
  f"generate 10 new advanced follow-up questions that go deeper "
  f"than these existing questions. Return ONLY a JSON array of strings. "
  f"No commentary, no markdown, just the JSON array.\n\n"
  f"Existing questions (avoid repeats):\n"
 )
 for q in existing_questions[-10:]:
  prompt += f"- {q}\n"
 try:
  provider, answer = router.think(prompt)
  if not answer:
   return []
  # Try to parse JSON array from response
  answer = answer.strip()
  # Handle markdown code blocks
  if answer.startswith("```"):
   lines = answer.split("\n")
   answer = "\n".join(lines[1:-1]) if len(lines) > 2 else answer
  if answer.startswith("["):
   questions = json.loads(answer)
   if isinstance(questions, list):
    return [str(q) for q in questions if isinstance(q, str) and len(q) > 10]
 except json.JSONDecodeError:
  pass
 except Exception as e:
  print(f"[WARN] Follow-up generation failed: {e}")
 return []


# =========================================================
# STATS PRINTER
# =========================================================

def print_stats():
 """Print harvest statistics summary."""
 print("\n" + "=" * 60)
 print("  HARVEST STATS SUMMARY")
 print("=" * 60)
 print(f"  Total harvested: {stats['total']}")
 print(f"  Errors/skipped:  {stats['errors']}")
 print(f"  Supabase writes: {stats['supabase_ok']}")
 print(f"  Fallback writes: {stats['fallback_ok']}")
 print()
 print("  By Domain:")
 for d, c in sorted(stats["by_domain"].items()):
  print(f"    {d}: {c}")
 print()
 print("  By Provider:")
 for p, c in sorted(stats["by_provider"].items()):
  print(f"    {p}: {c}")
 print("=" * 60 + "\n")


# =========================================================
# MAIN HARVEST LOOP
# =========================================================

def main():
 print("[HARVEST] Initializing Knowledge Harvester v1.0...")
 print(f"[HARVEST] Supabase endpoint: {SUPABASE_ENDPOINT}")
 print(f"[HARVEST] Fallback path: {FALLBACK_PATH}")
 print(f"[HARVEST] Supabase key present: {bool(SUPABASE_KEY)}")
 print()

 router = BrainRouter()
 print(f"[HARVEST] BrainRouter initialized with {len(router.providers)} providers")
 print()

 cycle = 0
 while True:
  cycle += 1
  print(f"\n[HARVEST] === CYCLE {cycle} START ===")

  # Build question queue for this cycle
  queue = []
  for domain, questions in DOMAINS.items():
   for q in questions:
    queue.append((domain, q))

  # Shuffle to distribute across providers evenly
  random.shuffle(queue)

  total_q = len(queue)
  for i, (domain, question) in enumerate(queue, 1):
   short_q = question[:50] + "..." if len(question) > 50 else question

   try:
    provider, answer = router.think(question)

    if not provider or not answer:
     print(f"[SKIP] Q{i}/{total_q} | No response | {short_q}")
     stats["errors"] += 1
     time.sleep(REQUEST_DELAY)
     continue

    print(f"[HARVEST] {domain} | {provider} | Q{i}/{total_q} | {short_q}")

    # Store the knowledge
    stored = store_knowledge(domain, question, provider, answer)
    if stored:
     stats["total"] += 1
     stats["by_domain"][domain] = stats["by_domain"].get(domain, 0) + 1
     stats["by_provider"][provider] = stats["by_provider"].get(provider, 0) + 1
    else:
     print(f"[WARN] Failed to store response for: {short_q}")
     stats["errors"] += 1

   except Exception as e:
    err_str = str(e)[:100]
    print(f"[ERROR] Q{i}/{total_q} | {err_str}")
    stats["errors"] += 1
    # On rate limit errors, wait longer
    if "429" in str(e) or "rate" in str(e).lower():
     print("[HARVEST] Rate limited -- sleeping 30s...")
     time.sleep(30)
    elif "401" in str(e) or "403" in str(e):
     print(f"[HARVEST] Auth error on provider -- continuing to next...")
     time.sleep(REQUEST_DELAY)
    else:
     time.sleep(REQUEST_DELAY)

   # Print stats every 50 questions
   if stats["total"] > 0 and stats["total"] % 50 == 0:
    print_stats()

   # Respect rate limits
   time.sleep(REQUEST_DELAY)

  # -- End of cycle: generate follow-up questions
  print(f"\n[HARVEST] === CYCLE {cycle} COMPLETE ===")
  print_stats()

  print("[HARVEST] Generating follow-up questions for next cycle...")
  for domain in list(DOMAINS.keys()):
   existing = DOMAINS[domain]
   new_qs = generate_followups(router, domain, existing)
   if new_qs:
    DOMAINS[domain].extend(new_qs)
    print(f"[HARVEST] +{len(new_qs)} new questions for {domain}")
   time.sleep(REQUEST_DELAY)

  print(f"[HARVEST] Total questions in pool: {sum(len(v) for v in DOMAINS.values())}")
  print(f"[HARVEST] Starting cycle {cycle + 1} in 10 seconds...")
  time.sleep(10)


if __name__ == "__main__":
 try:
  main()
 except KeyboardInterrupt:
  print("\n[HARVEST] Stopped by user.")
  print_stats()
 except Exception as e:
  print(f"\n[HARVEST] Fatal error: {e}")
  print_stats()
  raise