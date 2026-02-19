#!/bin/bash
# TCC Bridge — Watchdog V2.1
# Periodic health check and alerting

NTFY_TOPIC="tcc-zenith-hive"
CHECK_URL="http://localhost:8080/health"
PUBLIC_URL="https://zenith.cosmic-claw.com/health"

notify() {
    curl -H "Title: Bridge ALERT" -H "Priority: 5" -H "Tags: warning,skull" -d "$1" "https://ntfy.sh/$NTFY_TOPIC"
}

echo "[+] Watchdog V2.1 starting..."

while true; do
    if ! curl -s --fail "$CHECK_URL" > /dev/null; then
        echo "[!] LOCAL BRIDGE DOWN"
        notify "LOCAL BRIDGE DOWN! PM2 should restart it, but check logs: pm2 logs bridge"
    fi
    if ! curl -s --fail "$PUBLIC_URL" > /dev/null; then
        echo "[!] PUBLIC TUNNEL DOWN"
        notify "PUBLIC TUNNEL DOWN! zenith.cosmic-claw.com unreachable. Check cloudflared status."
    fi
    sleep 600
done
