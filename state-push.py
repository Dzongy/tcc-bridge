#!/usr/bin/env python3
"""TCC Bridge State Push (Cron Job)
Pushes device state to Supabase every 5 minutes via cron.
Works even if bridge.py is down.
"""
import subprocess, json, os, sys, time
from urllib.request import Request, urlopen

SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://vbqbbziqleymxcyesmky.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")
NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "tcc-zenith-hive")


def get_state():
    state = {"timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    try:
        r = subprocess.run("termux-battery-status", shell=True, capture_output=True, text=True, timeout=10)
        if r.returncode == 0:
            batt = json.loads(r.stdout)
            state["battery"] = batt.get("percentage", -1)
            state["charging"] = batt.get("status", "UNKNOWN")
    except Exception:
        state["battery"] = -1
    try:
        from urllib.request import urlopen as uo
        resp = uo("http://localhost:8080/health", timeout=5)
        state["bridge_alive"] = resp.status == 200
    except Exception:
        state["bridge_alive"] = False
    try:
        r = subprocess.run("pgrep -f cloudflared", shell=True, capture_output=True, text=True)
        state["tunnel_alive"] = r.returncode == 0
    except Exception:
        state["tunnel_alive"] = False
    try:
        r = subprocess.run("curl -s -o /dev/null -w '%{http_code}' --max-time 5 https://cloudflare.com",
                          shell=True, capture_output=True, text=True, timeout=10)
        state["internet"] = r.stdout.strip() == "200"
    except Exception:
        state["internet"] = False
    try:
        r = subprocess.run("hostname", shell=True, capture_output=True, text=True, timeout=5)
        state["hostname"] = r.stdout.strip()
    except Exception:
        state["hostname"] = "unknown"
    return state


def push_supabase(state):
    if not SUPABASE_KEY:
        print("No SUPABASE_KEY set, skipping push", file=sys.stderr)
        return False
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
        }).encode("utf-8")
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
            }).encode("utf-8")
            req = Request("https://ntfy.sh", data=payload, method="POST")
            req.add_header("Content-Type", "application/json")
            urlopen(req, timeout=10)
        except Exception:
            pass


if __name__ == "__main__":
    state = get_state()
    push_supabase(state)
    alert_if_down(state)
    print(json.dumps(state, indent=2))