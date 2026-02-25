#!/usr/bin/env python3
"""
ZENITH AUTONOMOUS TRADING MODULE v2.1
Jupiter DEX integration via public API
Wallet: 4MmoJTon34ukpNDRThoLGzP8LnGYNhcSVPVuCoUVuqz4
"""

import json
import logging
import urllib.request
import urllib.parse
import time
import os

# --- Configuration ---
WALLET = "4MmoJTon34ukpNDRThoLGzP8LnGYNhcSVPVuCoUVuqz4"
SOL_MINT = "So11111111111111111111111111111111111111112"
USDC_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
JUPITER_API = "https://public.jupiterapi.com"
SOLANA_RPC = "https://api.mainnet-beta.solana.com"

# Token whitelist
WHITELIST = [
    SOL_MINT, USDC_MINT,
    "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB",   # USDT
    "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263", # BONK
    "EKpQGSJtjMFqKZ9KQanSqYXRcF8fBopzLHYxdM65zcjm", # WIF
    "JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN",   # JUP
    "4k3Dyjzvzp8eMZWUXbBCjEvwSkkk59S5iCNLY3QrkX6R", # RAY
    "orcaEKTdK7LKz57vaAYr9QeNsVEPfiu6QeMU1kektZE",   # ORCA
    "HZ1JovNiVvGrGNiiYvEozEVgZ58xaU3RKwX8eACQBCt3", # PYTH
    "jtojtomepa8beP8AuQc6eXt5FriJwfFMwQx2v2f9mCL",   # JTO
]

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s"
)
logger = logging.getLogger("ZENITH-TRADE")


def _http_get(url):
    """HTTP GET with User-Agent to avoid Cloudflare blocks."""
    try:
        req = urllib.request.Request(url)
        req.add_header("User-Agent", "Zenith/2.1")
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        logger.error(f"HTTP GET failed: {url} -> {e}")
        return None


def _http_post(url, data):
    """HTTP POST JSON with User-Agent."""
    try:
        payload = json.dumps(data).encode()
        req = urllib.request.Request(url, data=payload, method="POST")
        req.add_header("Content-Type", "application/json")
        req.add_header("User-Agent", "Zenith/2.1")
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        logger.error(f"HTTP POST failed: {url} -> {e}")
        return None


def get_sol_balance():
    """Get SOL balance for wallet via Solana JSON-RPC."""
    try:
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getBalance",
            "params": [WALLET, {"commitment": "confirmed"}]
        }
        data = json.dumps(payload).encode()
        req = urllib.request.Request(SOLANA_RPC, data=data, method="POST")
        req.add_header("Content-Type", "application/json")
        req.add_header("User-Agent", "Zenith/2.1")
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read().decode())
        lamports = result.get("result", {}).get("value", 0)
        sol = lamports / 1_000_000_000
        logger.info(f"SOL Balance: {sol:.6f} SOL ({lamports} lamports)")
        return {"success": True, "sol": sol, "lamports": lamports, "wallet": WALLET}
    except Exception as e:
        logger.error(f"Balance check failed: {e}")
        return {"success": False, "error": str(e)}


def get_quote(input_mint, output_mint, amount_lamports, slippage_bps=50):
    """Get swap quote from Jupiter API."""
    try:
        params = urllib.parse.urlencode({
            "inputMint": input_mint,
            "outputMint": output_mint,
            "amount": str(amount_lamports),
            "slippageBps": str(slippage_bps),
        })
        url = f"{JUPITER_API}/quote?{params}"
        logger.info(f"Getting quote: {input_mint[:8]}... -> {output_mint[:8]}... amount={amount_lamports}")
        result = _http_get(url)
        if result and "outAmount" in result:
            out_amount = int(result["outAmount"])
            logger.info(f"Quote received: outAmount={out_amount}")
            return {"success": True, "quote": result, "outAmount": out_amount}
        else:
            error_msg = result.get("error", "Unknown error") if result else "No response"
            logger.warning(f"Quote failed: {error_msg}")
            return {"success": False, "error": error_msg}
    except Exception as e:
        logger.error(f"Quote error: {e}")
        return {"success": False, "error": str(e)}


def execute_swap(quote_response):
    """Execute a swap via Jupiter. Returns unsigned transaction for signing."""
    try:
        if not quote_response:
            return {"success": False, "error": "No quote provided"}
        swap_data = {
            "quoteResponse": quote_response,
            "userPublicKey": WALLET,
            "wrapAndUnwrapSol": True,
        }
        url = f"{JUPITER_API}/swap"
        logger.info("Requesting swap transaction from Jupiter...")
        result = _http_post(url, swap_data)
        if result and "swapTransaction" in result:
            logger.info("Swap transaction built successfully (unsigned)")
            return {
                "success": True,
                "swapTransaction": result["swapTransaction"],
                "note": "Transaction is unsigned. Requires wallet private key to sign and submit."
            }
        else:
            error_msg = result.get("error", "Unknown error") if result else "No response"
            logger.warning(f"Swap build failed: {error_msg}")
            return {"success": False, "error": error_msg}
    except Exception as e:
        logger.error(f"Swap error: {e}")
        return {"success": False, "error": str(e)}


def buy_token(token_mint, sol_amount):
    """Buy a token with SOL via Jupiter."""
    try:
        if token_mint not in WHITELIST:
            return {"success": False, "error": f"Token {token_mint[:8]}... not in whitelist"}
        lamports = int(sol_amount * 1_000_000_000)
        logger.info(f"BUY {token_mint[:8]}... with {sol_amount} SOL ({lamports} lamports)")
        quote_result = get_quote(SOL_MINT, token_mint, lamports)
        if not quote_result.get("success"):
            return quote_result
        swap_result = execute_swap(quote_result["quote"])
        return swap_result
    except Exception as e:
        logger.error(f"Buy error: {e}")
        return {"success": False, "error": str(e)}


def sell_token(token_mint, amount):
    """Sell a token for SOL via Jupiter."""
    try:
        if token_mint not in WHITELIST:
            return {"success": False, "error": f"Token {token_mint[:8]}... not in whitelist"}
        logger.info(f"SELL {amount} of {token_mint[:8]}... for SOL")
        quote_result = get_quote(token_mint, SOL_MINT, int(amount))
        if not quote_result.get("success"):
            return quote_result
        swap_result = execute_swap(quote_result["quote"])
        return swap_result
    except Exception as e:
        logger.error(f"Sell error: {e}")
        return {"success": False, "error": str(e)}


def get_portfolio():
    """Get current portfolio: SOL balance + token accounts."""
    try:
        portfolio = {"wallet": WALLET, "assets": []}
        # SOL balance
        bal = get_sol_balance()
        if bal.get("success"):
            portfolio["assets"].append({
                "symbol": "SOL",
                "mint": SOL_MINT,
                "balance": bal["sol"],
                "lamports": bal["lamports"],
            })
        # SPL token accounts
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getTokenAccountsByOwner",
            "params": [
                WALLET,
                {"programId": "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"},
                {"encoding": "jsonParsed", "commitment": "confirmed"}
            ]
        }
        data = json.dumps(payload).encode()
        req = urllib.request.Request(SOLANA_RPC, data=data, method="POST")
        req.add_header("Content-Type", "application/json")
        req.add_header("User-Agent", "Zenith/2.1")
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read().decode())
        accounts = result.get("result", {}).get("value", [])
        for acct in accounts:
            info = acct.get("account", {}).get("data", {}).get("parsed", {}).get("info", {})
            token_amount = info.get("tokenAmount", {})
            ui_amount = token_amount.get("uiAmount", 0)
            if ui_amount and ui_amount > 0:
                portfolio["assets"].append({
                    "mint": info.get("mint", "unknown"),
                    "balance": ui_amount,
                    "decimals": token_amount.get("decimals", 0),
                })
        logger.info(f"Portfolio: {len(portfolio['assets'])} assets found")
        return {"success": True, "portfolio": portfolio}
    except Exception as e:
        logger.error(f"Portfolio error: {e}")
        return {"success": False, "error": str(e)}


# --- Self-Test ---
if __name__ == "__main__":
    print("=" * 60)
    print("  ZENITH TRADING MODULE v2.1 - Self Test")
    print("=" * 60)
    print(f"  Wallet:  {WALLET}")
    print(f"  Jupiter: {JUPITER_API}")
    print(f"  RPC:     {SOLANA_RPC}")
    print("=" * 60)

    print("\n[1/3] Checking SOL balance...")
    bal = get_sol_balance()
    if bal["success"]:
        print(f"  -> {bal['sol']:.6f} SOL")
    else:
        print(f"  -> FAILED: {bal.get('error')}")

    print("\n[2/3] Fetching portfolio...")
    pf = get_portfolio()
    if pf["success"]:
        for a in pf["portfolio"]["assets"]:
            sym = a.get("symbol", a.get("mint", "?")[:8] + "...")
            print(f"  -> {sym}: {a['balance']}")
    else:
        print(f"  -> FAILED: {pf.get('error')}")

    print("\n[3/3] Test quote: 0.01 SOL -> USDC...")
    q = get_quote(SOL_MINT, USDC_MINT, 10_000_000, slippage_bps=50)
    if q["success"]:
        out = q["outAmount"]
        usdc_est = out / 1_000_000
        print(f"  -> Would receive ~{usdc_est:.4f} USDC")
    else:
        print(f"  -> FAILED: {q.get('error')}")

    print("\n" + "=" * 60)
    print("  Self-test complete. Module ready.")
    print("=" * 60)
