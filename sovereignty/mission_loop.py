#!/usr/bin/env python3
"""TCC SNIPER HIT SQUAD v3.0 --- Autonomous OODA Trading Loop"""
import json
import os
import sys
import time
import logging
from datetime import datetime

# Setup
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)
LOG_FILE = os.path.join(BASE_DIR, "mission_log.json")
CONFIG_FILE = os.path.join(BASE_DIR, "trading_config.json")

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(message)s")
log = logging.getLogger("sniper")

# Try importing trading functions
try:
    from zenith_trading import get_sol_balance, get_quote, buy_token, sell_token
    TRADING_LIVE = True
    log.info("Trading module loaded OK")
except ImportError as e:
    TRADING_LIVE = False
    log.warning(f"Trading module not available: {e}")

# HTTP helper using only stdlib
try:
    from urllib.request import Request, urlopen
    from urllib.parse import urlencode
    from urllib.error import URLError, HTTPError
except ImportError:
    log.error("urllib not available")
    sys.exit(1)

def http_post(url, data):
    """POST JSON data, return parsed response"""
    payload = json.dumps(data).encode("utf-8")
    req = Request(url, data=payload, headers={"Content-Type": "application/json"})
    try:
        with urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        log.error(f"HTTP POST failed: {e}")
        return None

def http_get(url):
    """GET request, return parsed JSON"""
    req = Request(url)
    try:
        with urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        log.error(f"HTTP GET failed: {e}")
        return None

# Config
def load_config():
    defaults = {
        "max_trade_sol": 0.15,
        "min_reserve_sol": 0.1,
        "slippage_bps": 50,
        "cooldown_seconds": 180,
        "cycle_seconds": 60,
        "council_url": "http://localhost:8888/chat",
        "jupiter_url": "https://public.jupiterapi.com",
        "watchlist": [
            "So11111111111111111111111111111111111111112",
            "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
            "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB",
            "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263",
            "JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN"
        ]
    }
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE) as f:
                loaded = json.load(f)
                defaults.update(loaded)
        except Exception:
            pass
    return defaults

# State
class SniperState:
    def __init__(self):
        self.trade_journal = []
        self.last_trade_time = 0
        self.win_streak = 0
        self.loss_streak = 0
        self.prices_cache = {}
        self.bullets_fired = 0
        self.bullets_reset_time = time.time()
        self.cycle_count = 0

state = SniperState()

# Journal
def log_trade(action, token, amount, confidence, result="pending"):
    entry = {
        "timestamp": datetime.now().isoformat(),
        "cycle": state.cycle_count,
        "action": action,
        "token": token[:8] + "..." if len(token) > 8 else token,
        "amount_sol": amount,
        "confidence": confidence,
        "result": result,
        "balance_after": get_balance_safe()
    }
    state.trade_journal.append(entry)
    try:
        existing = []
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE) as f:
                existing = json.load(f)
        existing.append(entry)
        with open(LOG_FILE, "w") as f:
            json.dump(existing, f, indent=2)
    except Exception as e:
        log.error(f"Journal write failed: {e}")
    return entry

def get_balance_safe():
    if TRADING_LIVE:
        try:
            result = get_sol_balance()
            if isinstance(result, dict) and 'sol' in result:
                return result['sol']
            return float(result) if result else -1
        except Exception:
            return -1
    return -1

# OBSERVE
def observe(config):
    log.info("=== OBSERVE ===")
    balance = get_balance_safe()
    log.info(f"SOL Balance: {balance}")
    
    if balance >= 0 and balance < config["min_reserve_sol"]:
        log.warning(f"Below reserve ({config['min_reserve_sol']} SOL) --- HOLD mode")
        return None
    
    sol_mint = "So11111111111111111111111111111111111111112"
    market_data = {"balance": balance, "tokens": {}, "timestamp": datetime.now().isoformat()}
    
    for token in config["watchlist"]:
        if token == sol_mint:
            continue
        try:
            url = f"{config['jupiter_url']}/quote?inputMint={sol_mint}&outputMint={token}&amount=100000000&slippageBps={config['slippage_bps']}"
            quote = http_get(url)
            if quote and "outAmount" in quote:
                price = int(quote["outAmount"])
                old_price = state.prices_cache.get(token, price)
                momentum = ((price - old_price) / old_price * 100) if old_price > 0 else 0
                state.prices_cache[token] = price
                market_data["tokens"][token] = {
                    "price": price,
                    "momentum_pct": round(momentum, 2)
                }
        except Exception as e:
            log.error(f"Quote scan failed for {token[:8]}: {e}")
    
    log.info(f"Scanned {len(market_data['tokens'])} tokens")
    return market_data

# ORIENT
def orient(market_data, config):
    log.info("=== ORIENT ===")
    if not market_data:
        return None
    
    prompt = f"""You are a Solana trading advisor. Analyze this market data and give ONE recommendation.

Balance: {market_data['balance']} SOL
Tokens scanned: {len(market_data['tokens'])}
Market data: {json.dumps(market_data['tokens'], indent=2)}

Respond in EXACTLY this format:
ACTION: BUY or SELL or HOLD
TOKEN: <mint address or NONE>
CONFIDENCE: <0-100>
REASON: <one sentence>"""

    response = http_post(config["council_url"], {"message": prompt})
    if response:
        text = response.get("response", response.get("text", str(response)))
        log.info(f"Council says: {text[:200]}")
        return text
    else:
        log.warning("Council unreachable --- defaulting to HOLD")
        return "ACTION: HOLD\nTOKEN: NONE\nCONFIDENCE: 0\nREASON: Council offline"

# DECIDE
def decide(council_response, config):
    log.info("=== DECIDE ===")
    if not council_response:
        return "HOLD", None, 0
    
    text = str(council_response).upper()
    
    action = "HOLD"
    if "ACTION: BUY" in text or "ACTION:BUY" in text:
        action = "BUY"
    elif "ACTION: SELL" in text or "ACTION:SELL" in text:
        action = "SELL"
    
    confidence = 0
    for line in text.split("\n"):
        if "CONFIDENCE" in line:
            nums = "".join(c for c in line if c.isdigit())
            if nums:
                confidence = min(int(nums), 100)
                break
    
    token = None
    for line in council_response.split("\n"):
        if "TOKEN:" in line.upper():
            t = line.split(":", 1)[1].strip()
            if t and t != "NONE" and len(t) > 10:
                token = t
                break
    
    if action == "BUY" and not token:
        movers = []
        for t, data in state.prices_cache.items():
            pass
        action = "HOLD"
    
    position_pct = 0
    if confidence >= 90:
        position_pct = 1.0
    elif confidence >= 75:
        position_pct = 0.75
    elif confidence >= 60:
        position_pct = 0.5
    elif confidence >= 50:
        position_pct = 0.25
    
    if state.loss_streak >= 3:
        position_pct *= 0.5
        log.warning(f"Loss streak {state.loss_streak} --- reducing position 50%")
    
    amount = config["max_trade_sol"] * position_pct
    
    log.info(f"Decision: {action} | Token: {str(token)[:8] if token else 'NONE'} | Confidence: {confidence} | Amount: {amount} SOL")
    return action, token, confidence

# ACT
def act(action, token, confidence, config):
    log.info("=== ACT ===")
    
    if action == "HOLD" or not token:
        log.info("HOLD --- no action taken")
        log_trade("HOLD", "NONE", 0, confidence, "skipped")
        return
    
    now = time.time()
    if now - state.last_trade_time < config["cooldown_seconds"]:
        remaining = config["cooldown_seconds"] - (now - state.last_trade_time)
        log.info(f"Cooldown active --- {remaining:.0f}s remaining")
        log_trade(action, token, 0, confidence, "cooldown")
        return
    
    balance = get_balance_safe()
    if balance < config["min_reserve_sol"]:
        log.warning("Below reserve --- cannot trade")
        log_trade(action, token, 0, confidence, "no_funds")
        return
    
    position_pct = 1.0 if confidence >= 90 else 0.75 if confidence >= 75 else 0.5 if confidence >= 60 else 0.25
    if state.loss_streak >= 3:
        position_pct *= 0.5
    amount = config["max_trade_sol"] * position_pct
    
    if not TRADING_LIVE:
        log.info(f"SIMULATED {action}: {amount} SOL on {token[:8]}...")
        log_trade(action, token, amount, confidence, "simulated")
        state.last_trade_time = now
        return
    
    try:
        if action == "BUY":
            result = buy_token(token, amount)
            log.info(f"BUY executed: {result}")
            log_trade("BUY", token, amount, confidence, "executed")
        elif action == "SELL":
            result = sell_token(token, amount)
            log.info(f"SELL executed: {result}")
            log_trade("SELL", token, amount, confidence, "executed")
        state.last_trade_time = now
    except Exception as e:
        log.error(f"Trade execution failed: {e}")
        log_trade(action, token, amount, confidence, f"error: {e}")

# MAIN OODA CYCLE
def mission_cycle(config):
    state.cycle_count += 1
    log.info(f"\n{'='*50}")
    log.info(f"MISSION CYCLE #{state.cycle_count} --- {datetime.now().strftime('%H:%M:%S')}")
    log.info(f"{'='*50}")
    
    market_data = observe(config)
    council_response = orient(market_data, config)
    action, token, confidence = decide(council_response, config)
    act(action, token, confidence, config)
    
    log.info(f"Cycle #{state.cycle_count} complete. Next scan in {config['cycle_seconds']}s")

def print_banner():
    banner = """
+==================================================+
|       TCC SNIPER HIT SQUAD v3.0                 |
|       Autonomous OODA Trading Loop              |
|       Commander: Dzongy                         |
|       Status: HUNTING                           |
+==================================================+
"""
    print(banner)
    log.info("Sniper initialized and scanning...")

if __name__ == "__main__":
    print_banner()
    config = load_config()
    log.info(f"Config loaded: max_trade={config['max_trade_sol']} SOL, reserve={config['min_reserve_sol']} SOL")
    log.info(f"Watchlist: {len(config['watchlist'])} tokens")
    log.info(f"Council: {config['council_url']}")
    log.info(f"Trading module: {'LIVE' if TRADING_LIVE else 'SIMULATED'}")
    
    while True:
        try:
            mission_cycle(config)
        except KeyboardInterrupt:
            log.info("Sniper stood down by Commander")
            break
        except Exception as e:
            log.error(f"Cycle error (recovering): {e}")
        time.sleep(config["cycle_seconds"])
