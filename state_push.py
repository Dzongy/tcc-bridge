#!/usr/bin/env python3
"""
TCC State Push
Kael the God Builder Edition
- Collects phone state: battery, network, last_seen, uptime, location (if permitted)
- Upserts to Supabase table 'device_state'
- Designed to be run via cron every ~10 minutes
"""

import json, os, sys, subprocess, time, socket, traceback
from urllib.request import urlopen, Request
from urllib.error   import URLError, HTTPError

# ─── CONFIG ───────────────────────────────────────────────────────────────────
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://vbqbbziqleymxcyesmky.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "sb_secret_lIbl-DBgdnrt_fejgJjKqg_qR62SVEm")
NTFY_HIVE    = os.environ.get("NTFY_HIVE",    "tcc-zenith-hive")
DEVICE_ID    = os.environ.get("DEVICE_ID",    socket.gethostname())
BRIDGE_PORT  = int(os.environ.get("PORT",     8765))
TIMEOUT      = 12   # seconds
LOG_FILE     = os.path.expanduser("~/tcc-state-push.log")

# ─── LOGGING ──────────────────────────────────────────────────────────────────
def _log(msg: str):
    stamp = time.strftime("%Y-%m-%d %H:%M:%S")
    line  = f"[{stamp}] {msg}"
    print(line, flush=True)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass

# ─── TERMUX HELPERS ───────────────────────────────────────────────────────────
def _termux_json(cmd: list) -> dict:
    """Run a termux-api command and parse its JSON output."""
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=TIMEOUT)
        if res.returncode == 0 and res.stdout.strip():
            return json.loads(res.stdout.strip())
    except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError):
        pass
    return {}


def get_battery() -> dict:
    raw = _termux_json(["termux-battery-status"])
    return {
        "battery_pct":     raw.get("percentage"),
        "battery_status":  raw.get("status"),          # CHARGING / DISCHARGING / FULL
        "battery_health":  raw.get("health"),
        "battery_plugged": raw.get("plugged"),
        "battery_temp":    raw.get("temperature"),
    }


def get_wifi() -> dict:
    raw = _termux_json(["termux-wifi-connectioninfo"])
    return {
        "wifi_ssid":      raw.get("ssid"),
        "wifi_bssid":     raw.get("bssid"),
        "wifi_rssi":      raw.get("rssi"),
        "wifi_link_speed":raw.get("link_speed_mbps"),
        "wifi_ip":        raw.get("ip"),
        "wifi_freq":      raw.get("frequency_mhz"),
    }


def get_network_type() -> dict:
    raw = _termux_json(["termux-telephony-deviceinfo"])
    return {
        "network_operator": raw.get("network_operator_name"),
        "network_type":     raw.get("network_type"),
        "sim_country":      raw.get("sim_country_iso"),
        "phone_type":       raw.get("phone_type"),
        "device_imei":      raw.get("device_id"),        # may be null without perms
    }


def get_signal_strength() -> dict:
    raw = _termux_json(["termux-telephony-cellinfo"])
    if isinstance(raw, list) and raw:
        cell = raw[0]
        return {
            "signal_type":   cell.get("type"),
            "signal_dbm":    cell.get("dbm"),
            "signal_level":  cell.get("level"),
            "signal_registered": cell.get("registered"),
        }
    return {"signal_type": None, "signal_dbm": None, "signal_level": None}


def get_location() -> dict:
    """Non-blocking best-effort location. Uses 'network' provider for speed."""
    raw = _termux_json(["termux-location", "-p", "network", "-r", "once"])
    return {
        "lat":      raw.get("latitude"),
        "lon":      raw.get("longitude"),
        "altitude": raw.get("altitude"),
        "accuracy": raw.get("accuracy"),
        "provider": raw.get("provider"),
    }


def get_bridge_uptime() -> float:
    """Check local bridge and extract uptime from /health."""
    try:
        req = Request(f"http://localhost:{BRIDGE_PORT}/health")
        with urlopen(req, timeout=4) as resp:
            body = json.loads(resp.read())
            return body.get("uptime", -1)
    except Exception:
        return -1


# ─── SUPABASE UPSERT ──────────────────────────────────────────────────────────
def supabase_upsert(table: str, payload: dict) -> bool:
    try:
        url  = f"{SUPABASE_URL}/rest/v1/{table}"
        body = json.dumps(payload).encode("utf-8")
        req  = Request(url, data=body, method="POST")
        req.add_header("apikey",        SUPABASE_KEY)
        req.add_header("Authorization", f"Bearer {SUPABASE_KEY}")
        req.add_header("Content-Type",  "application/json")
        req.add_header("Prefer",        "resolution=merge-duplicates,return=minimal")
        with urlopen(req, timeout=TIMEOUT) as resp:
            status = resp.status
            _log(f"[supabase] Upsert to '{table}' -> HTTP {status}")
            return status in (200, 201, 204)
    except HTTPError as e:
        _log(f"[supabase] HTTPError {e.code}: {e.read()[:200]}")
    except URLError as e:
        _log(f"[supabase] URLError: {e.reason}")
    except Exception as e:
        _log(f"[supabase] Error: {e}")
    return False


# ─── NTFY ALERT ───────────────────────────────────────────────────────────────
def ntfy_alert(title: str, msg: str, priority: str = "high"):
    try:
        req = Request(
            f"https://ntfy.sh/{NTFY_HIVE}",
            data=msg.encode("utf-8"),
            method="POST",
        )
        req.add_header("Title",    title)
        req.add_header("Tags",     "warning,robot")
        req.add_header("Priority", priority)
        urlopen(req, timeout=8)
    except Exception as e:
        _log(f"[ntfy] Failed: {e}")


# ─── MAIN ─────────────────────────────────────────────────────────────────────
def main() -> int:
    _log(f"=== State Push START — device={DEVICE_ID} ===")

    state = {
        "device_id": DEVICE_ID,
        "last_seen": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "timestamp": int(time.time()),
    }

    # Battery
    try:
        state.update(get_battery())
        _log(f"[battery] {state.get('battery_pct')}% {state.get('battery_status')}")
    except Exception as e:
        _log(f"[battery] Error: {e}")

    # WiFi
    try:
        state.update(get_wifi())
        _log(f"[wifi] SSID={state.get('wifi_ssid')} RSSI={state.get('wifi_rssi')}")
    except Exception as e:
        _log(f"[wifi] Error: {e}")

    # Network / SIM
    try:
        state.update(get_network_type())
        _log(f"[network] op={state.get('network_operator')} type={state.get('network_type')}")
    except Exception as e:
        _log(f"[network] Error: {e}")

    # Signal
    try:
        state.update(get_signal_strength())
        _log(f"[signal] dbm={state.get('signal_dbm')} level={state.get('signal_level')}")
    except Exception as e:
        _log(f"[signal] Error: {e}")

    # Location (best-effort, may be None if denied)
    try:
        state.update(get_location())
        _log(f"[location] lat={state.get('lat')} lon={state.get('lon')}")
    except Exception as e:
        _log(f"[location] Error: {e}")

    # Bridge uptime
    try:
        uptime = get_bridge_uptime()
        state["bridge_uptime_sec"] = uptime
        state["bridge_online"]     = uptime >= 0
        _log(f"[bridge] uptime={uptime}s online={state['bridge_online']}")
    except Exception as e:
        _log(f"[bridge] Error: {e}")
        state["bridge_online"] = False

    # Remove None values to avoid Supabase type errors on non-nullable cols
    clean_state = {k: v for k, v in state.items() if v is not None}

    _log(f"[state] Pushing {len(clean_state)} fields to Supabase.")
    ok = supabase_upsert("device_state", clean_state)

    if not ok:
        _log("[state] Supabase push FAILED.")
        ntfy_alert("State Push Failed", f"{DEVICE_ID}: Failed to push device state to Supabase.")
        return 1

    _log("=== State Push DONE ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
