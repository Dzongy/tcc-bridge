#!/usr/bin/env python3
"""
TCC State Push Daemon v7.0
Brain #10 — Kael

Runs as a separate PM2-managed process.
Periodically POSTs to /push_state on the local bridge server
as a belt-and-suspenders backup to the bridge's internal ReportThread.

This ensures Supabase is always updated even if the bridge's internal
reporting stalls due to network issues or thread deadlock.

Environment variables:
  BRIDGE_PORT         (default: 8080)
  BRIDGE_AUTH         (default: amos-bridge-2026)
  STATE_PUSH_INTERVAL (default: 300 — seconds between pushes)
"""

import time
import os
import sys
import logging
import traceback
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

# ── Config ──────────────────────────────────────────────────────────────────
PORT     = os.environ.get("BRIDGE_PORT", "8080")
AUTH     = os.environ.get("BRIDGE_AUTH", "amos-bridge-2026")
INTERVAL = int(os.environ.get("STATE_PUSH_INTERVAL", "300"))  # seconds
URL      = f"http://localhost:{PORT}/push_state"

MAX_RETRIES   = 4
RETRY_BACKOFF = [5, 15, 30, 60]

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [state-push] %(levelname)s — %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ]
)
log = logging.getLogger("tcc.state-push")


def push_state() -> bool:
    """POST to /push_state on the bridge. Returns True on success."""
    for attempt in range(MAX_RETRIES):
        try:
            req = Request(
                URL,
                data=b'{"source":"state-push-daemon"}',
                method="POST"
            )
            req.add_header("Authorization", AUTH)
            req.add_header("Content-Type",  "application/json")
            req.add_header("User-Agent",     "TCC-StatePush/7.0")
            with urlopen(req, timeout=20) as resp:
                body = resp.read().decode("utf-8", errors="replace")
                log.info("State push OK — HTTP %d | %s", resp.status, body[:120])
                return True
        except HTTPError as exc:
            log.warning("State push HTTP error (attempt %d/%d): %d %s",
                        attempt + 1, MAX_RETRIES, exc.code, exc.reason)
            # 401/403 — auth error, no point retrying
            if exc.code in (401, 403):
                log.error("Auth error — check BRIDGE_AUTH env var.")
                return False
        except URLError as exc:
            log.warning("State push URLError (attempt %d/%d): %s",
                        attempt + 1, MAX_RETRIES, exc.reason)
        except Exception:
            log.error("State push unexpected error (attempt %d/%d): %s",
                      attempt + 1, MAX_RETRIES, traceback.format_exc())
            return False  # don't retry unexpected errors

        if attempt < MAX_RETRIES - 1:
            wait = RETRY_BACKOFF[attempt]
            log.info("Retrying in %ds...", wait)
            time.sleep(wait)

    log.error("State push FAILED after %d attempts.", MAX_RETRIES)
    return False


def main():
    log.info("========================================")
    log.info("TCC State Push Daemon v7.0 starting.")
    log.info("  Target   : %s", URL)
    log.info("  Interval : %ds", INTERVAL)
    log.info("  Auth     : %s...", AUTH[:8])
    log.info("========================================")

    # Initial push after a short warmup delay
    log.info("Waiting 30s for bridge to start before first push...")
    time.sleep(30)

    consecutive_failures = 0

    while True:
        try:
            success = push_state()
            if success:
                consecutive_failures = 0
            else:
                consecutive_failures += 1
                log.warning("Consecutive failures: %d", consecutive_failures)
                if consecutive_failures >= 10:
                    log.critical(
                        "10 consecutive state push failures! "
                        "Bridge may be down. Waiting extended interval."
                    )
                    # Back off longer to avoid log spam
                    time.sleep(INTERVAL * 2)
                    consecutive_failures = 0
                    continue
        except Exception:
            log.error("Main loop error: %s", traceback.format_exc())

        log.debug("Sleeping %ds until next push.", INTERVAL)
        time.sleep(INTERVAL)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log.info("State push daemon stopped by user.")
        sys.exit(0)
    except Exception:
        log.critical("Fatal error in state push daemon: %s", traceback.format_exc())
        sys.exit(1)
