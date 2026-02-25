#!/bin/bash
# ============================================================
# ZENITH TRADING MODULE INSTALLER v1.0
# Sovereign On-Chain Trading via Jupiter DEX
# ============================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
MAGENTA='\033[0;35m'
BOLD='\033[1m'
NC='\033[0m'

ok()   { echo -e "${GREEN}[OK]${NC} $1"; }
info() { echo -e "${CYAN}[>>]${NC} $1"; }
warn() { echo -e "${YELLOW}[!!]${NC} $1"; }
fail() { echo -e "${RED}[FAIL]${NC} $1"; exit 1; }

echo ""
echo -e "${MAGENTA}============================================================${NC}"
echo -e "${MAGENTA}     ZENITH TRADING MODULE INSTALLER v1.0${NC}"
echo -e "${MAGENTA}     Jupiter DEX | Solana On-Chain | Autonomous${NC}"
echo -e "${MAGENTA}============================================================${NC}"
echo ""

# --------------------------------------------------
# Step 1: Install Python dependencies
# --------------------------------------------------
info "Installing Python dependencies..."
pip install solana solders requests base58 pynacl 2>/dev/null && ok "Dependencies installed" || warn "Some deps may have failed - continuing"

# --------------------------------------------------
# Step 2: Ensure target directory exists
# --------------------------------------------------
TARGET_DIR="$HOME/tcc-bridge/sovereignty"
mkdir -p "${TARGET_DIR}"
ok "Target directory: ${TARGET_DIR}"

# --------------------------------------------------
# Step 3: Create zenith_trading.py
# --------------------------------------------------
info "Writing zenith_trading.py..."

cat > "${TARGET_DIR}/zenith_trading.py" << 'TRADING_MODULE'
#!/usr/bin/env python3
"""
Zenith Trading Module v1.0
Sovereign on-chain trading via Jupiter DEX on Solana.
No exchange accounts. No KYC. Pure DeFi.
"""
import json
import logging
import time
import os
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
from urllib.parse import urlencode

# ============================================================
# CONSTANTS
# ============================================================
WALLET_ADDRESS = "4MmoJTon34ukpNDRThoLGzP8LnGYNhcSVPVuCoUVuqz4"
SOL_MINT = "So11111111111111111111111111111111111111112"
USDC_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
JUPITER_API = "https://quote-api.jup.ag/v6"
SOLANA_RPC = "https://api.mainnet-beta.solana.com"

TOKEN_REGISTRY = {
    "SOL":  {"mint": SOL_MINT,  "decimals": 9},
    "USDC": {"mint": USDC_MINT, "decimals": 6},
    "USDT": {"mint": "Es9vMFrzaCERmKfrEhGhKnS3au9YhGCsGRTGLqqnzGeP", "decimals": 6},
    "BONK": {"mint": "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263", "decimals": 5},
    "WIF":  {"mint": "EKpQGSJtjMFqKZ9KQanSqYXRcF8fBopzLHYxdM65zcjm", "decimals": 6},
    "JUP":  {"mint": "JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN",  "decimals": 6},
    "RAY":  {"mint": "4k3Dyjzvzp8eMZWUXbBCjEvwSkkk59S5iCNLY3QrkX6R", "decimals": 6},
    "ORCA": {"mint": "orcaEKTdK7LKz57vaAYr9QeNsVEPfiu6QeMU1kektZE",  "decimals": 6},
    "PYTH": {"mint": "HZ1JovNiVvGrGNiiYvEozEVgZ58xaU3RKwX8eACQBCt3", "decimals": 6},
    "JTO":  {"mint": "jtojtomepa8beP8AuQc6eXt5FriJwfFMwQx2v2f9mCL",  "decimals": 9},
}

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "trading_config.json")

def load_config():
    """Load trading configuration from disk."""
    try:
        with open(CONFIG_PATH, "r") as f:
            return json.load(f)
    except Exception:
        return {"max_trade_sol": 0.05, "slippage_bps": 50, "enabled": True}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [ZENITH-TRADE] %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
log = logging.getLogger("zenith_trading")

# ============================================================
# HELPER: HTTP requests
# ============================================================
def _http_get(url, timeout=15):
    req = Request(url)
    req.add_header("User-Agent", "Zenith/1.0")
    req.add_header("Accept", "application/json")
    resp = urlopen(req, timeout=timeout)
    return json.loads(resp.read().decode())

def _http_post(url, data, timeout=15):
    body = json.dumps(data).encode()
    req = Request(url, data=body, method="POST")
    req.add_header("User-Agent", "Zenith/1.0")
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "application/json")
    resp = urlopen(req, timeout=timeout)
    return json.loads(resp.read().decode())

def _rpc_call(method, params=None):
    payload = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params or []}
    return _http_post(SOLANA_RPC, payload)

# ============================================================
# CORE FUNCTIONS
# ============================================================
def get_sol_balance():
    """Get SOL balance for the treasury wallet."""
    try:
        result = _rpc_call("getBalance", [WALLET_ADDRESS, {"commitment": "confirmed"}])
        lamports = result.get("result", {}).get("value", 0)
        sol = lamports / 1e9
        log.info("SOL Balance: %.6f SOL (%d lamports)" % (sol, lamports))
        return {"success": True, "balance_sol": sol, "lamports": lamports, "wallet": WALLET_ADDRESS}
    except Exception as e:
        log.error("Failed to get SOL balance: %s" % str(e))
        return {"success": False, "error": str(e)}

def get_portfolio():
    """Get full portfolio: SOL balance + token accounts."""
    try:
        portfolio = {"wallet": WALLET_ADDRESS, "tokens": []}
        sol_data = get_sol_balance()
        if sol_data["success"]:
            portfolio["sol_balance"] = sol_data["balance_sol"]
            portfolio["sol_lamports"] = sol_data["lamports"]
        result = _rpc_call("getTokenAccountsByOwner", [
            WALLET_ADDRESS,
            {"programId": "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"},
            {"encoding": "jsonParsed", "commitment": "confirmed"}
        ])
        accounts = result.get("result", {}).get("value", [])
        for acc in accounts:
            info = acc.get("account", {}).get("data", {}).get("parsed", {}).get("info", {})
            mint = info.get("mint", "unknown")
            amount = info.get("tokenAmount", {})
            ui_amount = amount.get("uiAmount", 0)
            if ui_amount and ui_amount > 0:
                name = "UNKNOWN"
                for tname, tdata in TOKEN_REGISTRY.items():
                    if tdata["mint"] == mint:
                        name = tname
                        break
                portfolio["tokens"].append({
                    "name": name, "mint": mint,
                    "balance": ui_amount, "decimals": amount.get("decimals", 0)
                })
        log.info("Portfolio: %.4f SOL + %d tokens" % (sol_data.get("balance_sol", 0), len(portfolio["tokens"])))
        return {"success": True, "portfolio": portfolio}
    except Exception as e:
        log.error("Portfolio fetch failed: %s" % str(e))
        return {"success": False, "error": str(e)}

def get_quote(input_mint, output_mint, amount, slippage_bps=None):
    """Get a swap quote from Jupiter Aggregator."""
    try:
        cfg = load_config()
        if slippage_bps is None:
            slippage_bps = cfg.get("slippage_bps", 50)
        params = urlencode({
            "inputMint": input_mint, "outputMint": output_mint,
            "amount": str(amount), "slippageBps": str(slippage_bps),
            "onlyDirectRoutes": "false", "asLegacyTransaction": "false"
        })
        url = "%s/quote?%s" % (JUPITER_API, params)
        quote = _http_get(url)
        in_amount = int(quote.get("inAmount", 0))
        out_amount = int(quote.get("outAmount", 0))
        price_impact = quote.get("priceImpactPct", "0")
        log.info("Quote: %d -> %d (impact: %s%%)" % (in_amount, out_amount, price_impact))
        return {
            "success": True, "quote": quote,
            "in_amount": in_amount, "out_amount": out_amount,
            "price_impact_pct": float(price_impact),
            "route_plan": quote.get("routePlan", [])
        }
    except Exception as e:
        log.error("Quote failed: %s" % str(e))
        return {"success": False, "error": str(e)}

def execute_swap(quote_response):
    """Build swap transaction from Jupiter (unsigned)."""
    try:
        if not quote_response or not quote_response.get("success"):
            return {"success": False, "error": "Invalid quote response"}
        cfg = load_config()
        if not cfg.get("enabled", False):
            log.warning("Trading is DISABLED in config")
            return {"success": False, "error": "Trading disabled in config"}
        swap_data = {
            "quoteResponse": quote_response["quote"],
            "userPublicKey": WALLET_ADDRESS,
            "wrapAndUnwrapSol": True,
            "dynamicComputeUnitLimit": True,
            "prioritizationFeeLamports": "auto"
        }
        url = "%s/swap" % JUPITER_API
        result = _http_post(url, swap_data)
        swap_tx = result.get("swapTransaction")
        if swap_tx:
            log.info("Swap transaction built successfully (unsigned)")
            return {
                "success": True, "swap_transaction": swap_tx,
                "last_valid_block_height": result.get("lastValidBlockHeight"),
                "message": "Transaction built. Requires signing with wallet private key."
            }
        else:
            return {"success": False, "error": "No swap transaction returned", "raw": result}
    except Exception as e:
        log.error("Swap execution failed: %s" % str(e))
        return {"success": False, "error": str(e)}

def buy_token(token_mint, sol_amount):
    """Buy a token with SOL via Jupiter."""
    try:
        cfg = load_config()
        max_sol = cfg.get("max_trade_sol", 0.05)
        if sol_amount > max_sol:
            log.warning("Trade %.4f SOL exceeds max %.4f SOL - clamping" % (sol_amount, max_sol))
            sol_amount = max_sol
        if not cfg.get("enabled", False):
            return {"success": False, "error": "Trading disabled"}
        bal = get_sol_balance()
        if not bal["success"]:
            return {"success": False, "error": "Cannot check balance"}
        reserve = 0.05
        available = bal["balance_sol"] - reserve
        if sol_amount > available:
            return {"success": False, "error": "Insufficient SOL. Have %.4f, need %.4f + %.4f reserve" % (bal["balance_sol"], sol_amount, reserve)}
        lamports = int(sol_amount * 1e9)
        log.info("BUY: Spending %.4f SOL on %s" % (sol_amount, token_mint))
        quote = get_quote(SOL_MINT, token_mint, lamports)
        if not quote["success"]:
            return quote
        if quote["price_impact_pct"] > 5.0:
            return {"success": False, "error": "Price impact %.2f%% exceeds 5%% limit" % quote["price_impact_pct"]}
        result = execute_swap(quote)
        result["action"] = "BUY"
        result["token_mint"] = token_mint
        result["sol_spent"] = sol_amount
        result["estimated_output"] = quote["out_amount"]
        return result
    except Exception as e:
        log.error("Buy failed: %s" % str(e))
        return {"success": False, "error": str(e)}

def sell_token(token_mint, amount):
    """Sell a token for SOL via Jupiter."""
    try:
        cfg = load_config()
        if not cfg.get("enabled", False):
            return {"success": False, "error": "Trading disabled"}
        log.info("SELL: %s of %s for SOL" % (str(amount), token_mint))
        quote = get_quote(token_mint, SOL_MINT, int(amount))
        if not quote["success"]:
            return quote
        if quote["price_impact_pct"] > 5.0:
            return {"success": False, "error": "Price impact %.2f%% exceeds 5%% limit" % quote["price_impact_pct"]}
        result = execute_swap(quote)
        result["action"] = "SELL"
        result["token_mint"] = token_mint
        result["amount_sold"] = amount
        result["estimated_sol_out"] = quote["out_amount"]
        return result
    except Exception as e:
        log.error("Sell failed: %s" % str(e))
        return {"success": False, "error": str(e)}

if __name__ == "__main__":
    import sys
    print("\n=== ZENITH TRADING MODULE v1.0 ===")
    print("Wallet: %s" % WALLET_ADDRESS)
    print("Jupiter API: %s" % JUPITER_API)
    cfg = load_config()
    print("Trading Enabled: %s" % cfg.get("enabled"))
    print("Max Trade: %s SOL" % cfg.get("max_trade_sol"))
    print("Slippage: %s bps" % cfg.get("slippage_bps"))
    print()
    print("[1/3] Checking SOL balance...")
    bal = get_sol_balance()
    print("  -> %s" % json.dumps(bal, indent=2))
    print()
    print("[2/3] Fetching portfolio...")
    port = get_portfolio()
    print("  -> SOL: %s" % port.get("portfolio", {}).get("sol_balance", "N/A"))
    for t in port.get("portfolio", {}).get("tokens", []):
        print("  -> %s: %s" % (t["name"], t["balance"]))
    print()
    print("[3/3] Test quote: 0.01 SOL -> USDC...")
    q = get_quote(SOL_MINT, USDC_MINT, 10000000)
    if q["success"]:
        print("  -> Would receive: %s USDC (raw)" % q["out_amount"])
        print("  -> Price impact: %s%%" % q["price_impact_pct"])
    else:
        print("  -> Quote failed: %s" % q.get("error"))
    print()
    print("=== SELF-TEST COMPLETE ===")
TRADING_MODULE

ok "zenith_trading.py written ($(wc -c < \"${TARGET_DIR}/zenith_trading.py\") bytes)"

# --------------------------------------------------
# Step 4: Create trading_config.json
# --------------------------------------------------
info "Writing trading_config.json..."

cat > "${TARGET_DIR}/trading_config.json" << 'TRADING_CONFIG'
{
    "max_trade_sol": 0.05,
    "slippage_bps": 50,
    "enabled": true,
    "reserve_sol": 0.05,
    "max_price_impact_pct": 5.0,
    "max_daily_trades": 20,
    "token_whitelist": ["SOL", "USDC", "USDT", "BONK", "WIF", "JUP", "RAY", "ORCA", "PYTH", "JTO"],
    "wallet": "4MmoJTon34ukpNDRThoLGzP8LnGYNhcSVPVuCoUVuqz4",
    "version": "1.0"
}
TRADING_CONFIG

ok "trading_config.json written"

# --------------------------------------------------
# Step 5: Verify
# --------------------------------------------------
echo ""
info "Verifying installation..."
[ -f "${TARGET_DIR}/zenith_trading.py" ] && ok "zenith_trading.py EXISTS" || fail "zenith_trading.py MISSING"
[ -f "${TARGET_DIR}/trading_config.json" ] && ok "trading_config.json EXISTS" || fail "trading_config.json MISSING"

echo ""
echo -e "${GREEN}============================================================${NC}"
echo -e "${GREEN}  Zenith Trading Module ACTIVE${NC}"
echo -e "${GREEN}============================================================${NC}"
echo -e "  Wallet:    ${CYAN}4MmoJTon34ukpNDRThoLGzP8LnGYNhcSVPVuCoUVuqz4${NC}"
echo -e "  Jupiter:   ${CYAN}https://quote-api.jup.ag/v6${NC}"
echo -e "  Max Trade: ${YELLOW}0.05 SOL${NC}"
echo -e "  Slippage:  ${YELLOW}50 bps${NC}"
echo -e "${GREEN}============================================================${NC}"
echo ""
echo -e "  ${BOLD}Run self-test:${NC}"
echo -e "    cd ~/tcc-bridge/sovereignty && python3 zenith_trading.py"
echo ""
echo -e "  ${BOLD}Import in code:${NC}"
echo -e "    from zenith_trading import buy_token, sell_token, get_portfolio"
echo ""
echo -e "${MAGENTA}  ZENITH IS SOVEREIGN. ZENITH TRADES FREE.${NC}"
echo ""