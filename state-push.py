#!/usr/bin/env python3
"""
TCC Bridge — State Push (PM2 managed)
Built on Xena bridge_v2.py push architecture.
PM2 restarts this every 5 minutes (restart_delay: 300000).
Reports device state to Supabase + alerts via ntfy if services down.
"""
import subprocess, json, os, sys, time
from urllib.request import Request, urlopen

SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://vbqbbziqleymxcyesmky.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "sb_secret_lIbl-DBgdnrt_fejgJjKqg_qR62SVEm")
NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "tcc-zenith-hive")


def get_state():
    state = {"timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    # Battery
    try:
        r = subprocess.run("termux-battery-status", shell=True, capture_output=True, text=True, timeout=10)
        if r.returncode == 0:
            batt = json.loads(r.stdout)
            state["battery"] = batt.get("percentage", -1)
            state["charging"] = batt.get("status", "UNKNOWN")
    except: state["battery"] = -1
    # Bridge health
    try:
        resp = urlopen("http://localhost:8080/health", timeout=5)
        state["bridge_alive"] = resp.status == 200
    except: state["bridge_alive"] = False
    # Cloudflared
    try:
        r = subprocess.run("pgrep -f cloudflared", shell=True, capture_output=True, text=True)
        state["tunnel_alive"] = r.returncode == 0
    except: state["tunnel_alive"] = False
    # Internet
    try:
        resp = urlopen("https://cloudflare.com", timeout=5)
        state["internet"] = resp.status == 200
    except: state["internet"] = False
    # Hostname
    try:
        r = subprocess.run("hostname", shell=True, capture_output=True, text=True, timeout=5)
        state["hostname"] = r.stdout.strip()
    except: state["hostname"] = "unknown"
    return state


def push_supabase(state):
    if not SUPABASE_KEY: return False
    try:
        payload = json.dumps({
            "device_id": "amos-arms",
            "battery": state.get("battery", -1),
            "hostname": state.get("hostname", "unknown"),
            "network": "internet={}, bridge={}, tunnel={}".format(
                "OK" if state.get("internet") else "DOWN",
                "OK" if state.get("bridge_alive") else "DOWN",
                "OK" if state.get("tunnel_alive") else "DOWN"),
            "raw_output": json.dumps(state),
        }).encode()
        req = Request(SUPABASE_URL + "/rest/v1/device_state", data=payload, method="POST")
        req.add_header("apikey", SUPABASE_KEY)
        req.add_header("Authorization", "Bearer " + SUPABASE_KEY)
        req.add_header("Content-Type", "application/json")
        req.add_header("Prefer", "resolution=merge-duplicates")
        urlopen(req, timeout=10)
        return True
    except Exception as e:
        print("Supabase push failed: " + str(e), file=sys.stderr)
        return False


def alert_if_down(state):
    problems = []
    if not state.get("bridge_alive"): problems.append("Bridge DOWN")
    if not state.get("tunnel_alive"): problems.append("Tunnel DOWN")
    if not state.get("internet"): problems.append("Internet DOWN")
    if problems:
        msg = ", ".join(problems)
        try:
            payload = json.dumps({
                "topic": NTFY_TOPIC,
                "title": "BRIDGE ALERT",
                "message": "State check: " + msg + ". Battery: " + str(state.get("battery", "?")) + "%",
                "priority": 5,
                "tags": ["warning", "rotating_light"],
            }).encode()
            req = Request("https://ntfy.sh", data=payload, method="POST")
            req.add_header("Content-Type", "application/json")
            urlopen(req, timeout=10)
        except: pass


if __name__ == "__main__":
    state = get_state()
    pushed = push_supabase(state)
    alert_if_down(state)
    print(json.dumps(state, indent=2))
    # Exit so PM2 restart_delay handles the 5-min interval
    sys.exit(0)