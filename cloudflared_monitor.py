#!/usr/bin/env python3
# =============================================================================
# TCC Cloudflared Monitor
# Watches the tunnel health URL. If it dies, restarts the PM2 tunnel process.
# =============================================================================

import time
import logging
import subprocess
import sys
import os
import urllib.request
import urllib.error

# --- Config ---
HEALTH_URL = os.environ.get('HEALTH_URL', 'https://zenith.cosmic-claw.com/health')
CHECK_INTERVAL = int(os.environ.get('MONITOR_INTERVAL', 60))  # seconds
FAIL_THRESHOLD = int(os.environ.get('FAIL_THRESHOLD', 3))       # consecutive fails before restart
PM2_PROCESS = os.environ.get('PM2_PROCESS', 'tcc-tunnel')
RESTART_COOLDOWN = int(os.environ.get('RESTART_COOLDOWN', 120))  # seconds after restart before re-checking

# --- Logging ---
log_dir = os.path.expanduser('~/tcc')
os.makedirs(log_dir, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [MONITOR] %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(log_dir, 'monitor.log')),
        logging.StreamHandler(sys.stdout)
    ]
)
log = logging.getLogger('TCC-Monitor')

# =============================================================================
# FUNCTIONS
# =============================================================================

def check_health():
    """Returns True if health URL responds with 200, False otherwise."""
    try:
        req = urllib.request.Request(HEALTH_URL)
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status == 200:
                log.debug(f'Health check PASS: {HEALTH_URL} -> {resp.status}')
                return True
            else:
                log.warning(f'Health check WARN: {HEALTH_URL} -> {resp.status}')
                return False
    except urllib.error.URLError as e:
        log.warning(f'Health check FAIL (URLError): {e.reason}')
        return False
    except Exception as e:
        log.warning(f'Health check FAIL (Exception): {e}')
        return False


def restart_tunnel():
    """Execute pm2 restart on the tunnel process."""
    log.warning(f'Restarting PM2 process: {PM2_PROCESS}')
    try:
        result = subprocess.run(
            ['pm2', 'restart', PM2_PROCESS],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode == 0:
            log.info(f'PM2 restart SUCCESS: {PM2_PROCESS}')
            log.info(f'stdout: {result.stdout.strip()}')
        else:
            log.error(f'PM2 restart FAILED (rc={result.returncode}): {result.stderr.strip()}')
    except subprocess.TimeoutExpired:
        log.error('PM2 restart command timed out.')
    except FileNotFoundError:
        log.error('pm2 not found in PATH. Cannot restart tunnel.')
    except Exception as e:
        log.error(f'Unexpected error during PM2 restart: {e}')


# =============================================================================
# MAIN LOOP
# =============================================================================

def main():
    log.info('=' * 60)
    log.info('TCC Cloudflared Monitor STARTED')
    log.info(f'  Health URL    : {HEALTH_URL}')
    log.info(f'  Check Interval: {CHECK_INTERVAL}s')
    log.info(f'  Fail Threshold: {FAIL_THRESHOLD} consecutive failures')
    log.info(f'  PM2 Process   : {PM2_PROCESS}')
    log.info('=' * 60)

    consecutive_failures = 0

    while True:
        try:
            ok = check_health()
            if ok:
                if consecutive_failures > 0:
                    log.info(f'Tunnel RECOVERED after {consecutive_failures} failure(s).')
                consecutive_failures = 0
                log.info(f'Tunnel healthy. Next check in {CHECK_INTERVAL}s.')
            else:
                consecutive_failures += 1
                log.warning(
                    f'Tunnel UNHEALTHY. Consecutive failures: {consecutive_failures}/{FAIL_THRESHOLD}'
                )
                if consecutive_failures >= FAIL_THRESHOLD:
                    log.error(
                        f'Failure threshold reached ({FAIL_THRESHOLD}). Triggering restart.'
                    )
                    restart_tunnel()
                    consecutive_failures = 0
                    log.info(f'Cooling down for {RESTART_COOLDOWN}s after restart...')
                    time.sleep(RESTART_COOLDOWN)
                    continue
        except Exception as e:
            log.error(f'Monitor loop error: {e}')

        time.sleep(CHECK_INTERVAL)


if __name__ == '__main__':
    main()
