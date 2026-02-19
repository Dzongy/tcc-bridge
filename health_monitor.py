#!/usr/bin/env python3
"""
TCC Health Monitor
Kael the God Builder Edition
- Checks bridge on localhost:8765/health
- Checks bridge on zenith.cosmic-claw.com/health
- Restarts PM2 if down
- Alerts via ntfy tcc-zenith-hive
- Designed to run from cron every 5 minutes
"""

import json, os, sys, subprocess, time, socket
from urllib.request import urlopen, Request
from urllib.error   import URLError, HTTPError

# ─── CONFIG ───────────────────────────────────────────────────────────────────
LOCAL_URL    = "http://localhost:8765/health"
REMOTE_URL   = "https://zenith.cosmic-claw.com/health"
NTFY_TOPIC   = "tcc-zenith-hive"
DEVICE_ID    = os.environ.get("DEVICE_ID", socket.gethostname())
TIMEOUT      = 10   # seconds per request
PM2_PATH     = os.environ.get("PM2_PATH", "pm2")
FLAG_FILE    = os.path.expanduser("~/.tcc_health_down_flag")
MAX_RESTARTS = 3    # max consecutive PM2 restarts before escalating
LOG_FILE     = os.path.expanduser("~/tcc-health.log")

# ─── HELPERS ──────────────────────────────────────────────────────────────────
def _log(msg: str):
    stamp = time.strftime("%Y-%m-%d %H:%M:%S")
    line  = f"[{stamp}] {msg}"
    print(line, flush=True)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def ntfy(title: str, msg: str, priority: str = "high", tags: str = "warning,robot"):
    try:
        req = Request(
            f"https://ntfy.sh/{NTFY_TOPIC}",
            data=msg.encode("utf-8"),
            method="POST",
        )
        req.add_header("Title",    title)
        req.add_header("Tags",     tags)
        req.add_header("Priority", priority)
        urlopen(req, timeout=8)
        _log(f"[ntfy] Alert sent: {title}")
    except Exception as e:
        _log(f"[ntfy] FAILED to send alert: {e}")


def check_endpoint(url: str) -> dict:
    """Returns dict with keys: ok, status_code, body, error"""
    try:
        req = Request(url)
        req.add_header("X-Auth", "amos-bridge-2026")  # for ghost server compat
        with urlopen(req, timeout=TIMEOUT) as resp:
            body = resp.read(512).decode("utf-8", errors="replace")
            return {"ok": resp.status == 200, "status_code": resp.status, "body": body, "error": None}
    except HTTPError as e:
        return {"ok": False, "status_code": e.code, "body": "", "error": str(e)}
    except (URLError, OSError) as e:
        return {"ok": False, "status_code": None, "body": "", "error": str(e)}
    except Exception as e:
        return {"ok": False, "status_code": None, "body": "", "error": str(e)}


def read_flag() -> int:
    """Read consecutive failure count from flag file."""
    try:
        with open(FLAG_FILE) as f:
            return int(f.read().strip())
    except Exception:
        return 0


def write_flag(count: int):
    try:
        with open(FLAG_FILE, "w") as f:
            f.write(str(count))
    except Exception:
        pass


def clear_flag():
    try:
        os.remove(FLAG_FILE)
    except Exception:
        pass


def restart_pm2(app: str = "tcc-bridge") -> bool:
    try:
        result = subprocess.run(
            [PM2_PATH, "restart", app],
            capture_output=True, text=True, timeout=30
        )
        _log(f"[pm2] restart {app}: code={result.returncode} stdout={result.stdout.strip()[:200]}")
        return result.returncode == 0
    except Exception as e:
        _log(f"[pm2] restart failed: {e}")
        return False


def restart_all_pm2() -> bool:
    try:
        result = subprocess.run(
            [PM2_PATH, "restart", "all"],
            capture_output=True, text=True, timeout=45
        )
        _log(f"[pm2] restart all: code={result.returncode}")
        return result.returncode == 0
    except Exception as e:
        _log(f"[pm2] restart all failed: {e}")
        return False


# ─── MAIN ─────────────────────────────────────────────────────────────────────
def main():
    _log("=== TCC Health Monitor run ===")

    local  = check_endpoint(LOCAL_URL)
    remote = check_endpoint(REMOTE_URL)

    _log(f"[local]  ok={local['ok']}  status={local['status_code']}  err={local['error']}")
    _log(f"[remote] ok={remote['ok']} status={remote['status_code']} err={remote['error']}")

    if local["ok"] and remote["ok"]:
        _log("[health] ALL GOOD — clearing failure flag.")
        clear_flag()
        return 0

    # At least one endpoint is down
    fail_count = read_flag() + 1
    write_flag(fail_count)
    _log(f"[health] DOWN — consecutive failure count: {fail_count}")

    if not local["ok"]:
        _log("[health] Local bridge DOWN. Attempting PM2 restart.")
        ok = restart_pm2("tcc-bridge")
        if ok:
            time.sleep(8)  # give it time to come up
            recheck = check_endpoint(LOCAL_URL)
            if recheck["ok"]:
                _log("[health] Bridge recovered after restart.")
                ntfy(
                    "Bridge Recovered",
                    f"{DEVICE_ID}: Bridge was down but recovered after PM2 restart.",
                    priority="default",
                    tags="white_check_mark,robot",
                )
                clear_flag()
                return 0
            else:
                _log("[health] Bridge STILL down after restart.")

    if fail_count >= MAX_RESTARTS:
        _log(f"[health] {fail_count} consecutive failures. Restarting ALL pm2 apps.")
        restart_all_pm2()
        ntfy(
            "Bridge CRITICAL — Multiple Restarts",
            f"{DEVICE_ID}: Bridge has failed {fail_count} consecutive health checks.\n"
            f"Local: {local}\nRemote: {remote}\nAttempted full PM2 restart.",
            priority="urgent",
            tags="fire,sos",
        )
    else:
        ntfy(
            "Bridge DOWN",
            f"{DEVICE_ID}: Bridge health check failed (attempt {fail_count}).\n"
            f"Local ok={local['ok']} ({local['error']})\n"
            f"Remote ok={remote['ok']} ({remote['error']})",
            priority="high",
            tags="warning,robot",
        )

    return 1


if __name__ == "__main__":
    sys.exit(main())
