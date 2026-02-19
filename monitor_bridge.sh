#!/data/data/com.termux/files/usr/bin/bash
# Health Monitor for Bridge V2
HEALTH_URL="http://localhost:8765/health"
NTFY_URL="https://ntfy.sh/tcc-zenith-hive"

check_health() {
    RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" "$HEALTH_URL")
    if [ "$RESPONSE" != "200" ]; then
        curl -d "CRITICAL: Bridge V2 Health Check FAILED (HTTP $RESPONSE)" "$NTFY_URL"
        pm2 restart tcc-bridge
    fi
}

check_tunnel() {
    if ! pm2 jlist | grep -q '"name":"tcc-tunnel","status":"online"'; then
        curl -d "WARNING: Cloudflare Tunnel DOWN. Restarting..." "$NTFY_URL"
        pm2 restart tcc-tunnel
    fi
}

check_health
check_tunnel
