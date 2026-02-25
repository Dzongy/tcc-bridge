#!/usr/bin/env python3
"""twin_bridge.py - Zenith -> Twin API Dispatch Bridge
Allows Zenith to dispatch tasks to Twin's cloud capabilities.
Twin handles: browser automation, deep research, platform scraping, content creation.
"""
import json, os, time, urllib.request, urllib.error
from datetime import datetime

TWIN_API_URL = os.environ.get("TWIN_API_URL", "http://localhost:3000/api/dispatch")
LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "twin_dispatch_log.json")
MAX_RETRIES = 3
RETRY_DELAY = 2

def _log_dispatch(task_type, payload, result, success):
    """Append dispatch record to log file."""
    try:
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE, "r") as f:
                log = json.load(f)
        else:
            log = []
        log.append({
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "task_type": task_type,
            "payload": payload,
            "success": success,
            "result_preview": str(result)[:500] if result else None
        })
        # Keep last 500 entries
        if len(log) > 500:
            log = log[-500:]
        with open(LOG_FILE, "w") as f:
            json.dump(log, f, indent=2)
    except Exception as e:
        print(f"[TWIN_BRIDGE] Log write failed: {e}")

def _post(endpoint, payload, task_type):
    """POST to Twin API with retry logic."""
    url = TWIN_API_URL.rstrip("/") + "/" + endpoint
    data = json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json", "User-Agent": "Zenith/1.0"}
    
    twin_key = os.environ.get("TWIN_API_KEY", "")
    if twin_key:
        headers["Authorization"] = f"Bearer {twin_key}"
    
    last_err = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            req = urllib.request.Request(url, data=data, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=120) as resp:
                body = json.loads(resp.read().decode("utf-8"))
                _log_dispatch(task_type, payload, body, True)
                return {"success": True, "data": body, "status": resp.status}
        except urllib.error.HTTPError as e:
            last_err = f"HTTP {e.code}: {e.reason}"
            err_body = e.read().decode("utf-8", errors="replace")[:300] if e.fp else ""
            print(f"[TWIN_BRIDGE] Attempt {attempt}/{MAX_RETRIES} failed: {last_err} {err_body}")
        except urllib.error.URLError as e:
            last_err = f"URLError: {e.reason}"
            print(f"[TWIN_BRIDGE] Attempt {attempt}/{MAX_RETRIES} failed: {last_err}")
        except Exception as e:
            last_err = str(e)
            print(f"[TWIN_BRIDGE] Attempt {attempt}/{MAX_RETRIES} failed: {last_err}")
        
        if attempt < MAX_RETRIES:
            time.sleep(RETRY_DELAY * attempt)
    
    result = {"success": False, "error": last_err}
    _log_dispatch(task_type, payload, result, False)
    return result

def dispatch_research(topic, depth="standard"):
    """Dispatch a deep research task to Twin.
    Args:
        topic: Research question or topic string
        depth: 'standard' for web_search, 'deep' for deep_research
    Returns:
        dict with success, data/error keys
    """
    return _post("research", {
        "topic": topic,
        "depth": depth,
        "requested_by": "zenith"
    }, "research")

def dispatch_scrape(url, fmt="summary"):
    """Dispatch a URL scrape task to Twin.
    Args:
        url: Target URL to scrape
        fmt: 'summary' or 'markdown'
    Returns:
        dict with success, data/error keys
    """
    return _post("scrape", {
        "url": url,
        "format": fmt,
        "requested_by": "zenith"
    }, "scrape")

def dispatch_browser_task(instructions, start_url=""):
    """Dispatch a browser automation task to Twin.
    Args:
        instructions: Natural language instructions for the browser agent
        start_url: Optional starting URL
    Returns:
        dict with success, data/error keys
    """
    return _post("browser", {
        "instructions": instructions,
        "start_url": start_url,
        "requested_by": "zenith"
    }, "browser")

def dispatch_sentiment(platforms=None, keywords=None):
    """Dispatch a sentiment scraping task to Twin.
    Args:
        platforms: List of platforms ['reddit','twitter','tiktok']
        keywords: List of keywords to search
    Returns:
        dict with success, data/error keys
    """
    return _post("sentiment", {
        "platforms": platforms or ["reddit", "twitter"],
        "keywords": keywords or ["solana", "crypto", "memecoin"],
        "requested_by": "zenith"
    }, "sentiment")

def dispatch_email(to, subject, body):
    """Dispatch an email send task to Twin.
    Args:
        to: Recipient email
        subject: Email subject
        body: Email body text
    Returns:
        dict with success, data/error keys
    """
    return _post("email", {
        "to": to,
        "subject": subject,
        "body": body,
        "requested_by": "zenith"
    }, "email")

def get_dispatch_log(last_n=20):
    """Read the last N dispatch log entries."""
    try:
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE, "r") as f:
                log = json.load(f)
            return log[-last_n:]
        return []
    except Exception:
        return []

def get_dispatch_stats():
    """Get summary stats from dispatch log."""
    try:
        log = get_dispatch_log(500)
        total = len(log)
        success = sum(1 for e in log if e.get("success"))
        by_type = {}
        for e in log:
            t = e.get("task_type", "unknown")
            by_type[t] = by_type.get(t, 0) + 1
        return {
            "total_dispatches": total,
            "successful": success,
            "failed": total - success,
            "success_rate": round(success / total * 100, 1) if total else 0,
            "by_type": by_type
        }
    except Exception:
        return {"total_dispatches": 0}

if __name__ == "__main__":
    print("[TWIN_BRIDGE] Zenith -> Twin API Bridge v1.0")
    print(f"[TWIN_BRIDGE] API URL: {TWIN_API_URL}")
    print(f"[TWIN_BRIDGE] Log file: {LOG_FILE}")
    print("[TWIN_BRIDGE] Functions: dispatch_research, dispatch_scrape, dispatch_browser_task, dispatch_sentiment, dispatch_email")
    print("[TWIN_BRIDGE] Status: READY (connect Twin API to activate)")
    stats = get_dispatch_stats()
    print(f"[TWIN_BRIDGE] Dispatch history: {stats['total_dispatches']} total")
