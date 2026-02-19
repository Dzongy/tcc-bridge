#!/data/data/com.termux/files/usr/bin/bash
# =============================================================================
# Termux Boot Script
# Location: ~/.termux/boot/start-tcc.sh
# This runs automatically when the device boots (requires Termux:Boot app)
# =============================================================================

# Give Android time to fully initialize networking
sleep 15

# Log file for boot script
BOOT_LOG="$HOME/tcc/logs/boot.log"
mkdir -p "$HOME/tcc/logs"

echo "$(date '+%Y-%m-%d %H:%M:%S') [BOOT] Termux boot script triggered" >> "$BOOT_LOG"

# --- Add bin to PATH ---
export PATH="$HOME/bin:/data/data/com.termux/files/usr/bin:$PATH"

# --- Load environment variables ---
if [ -f "$HOME/tcc/.env" ]; then
    export $(grep -v '^#' "$HOME/tcc/.env" | grep -v '^$' | xargs) 2>/dev/null || true
    echo "$(date '+%Y-%m-%d %H:%M:%S') [BOOT] .env loaded" >> "$BOOT_LOG"
else
    echo "$(date '+%Y-%m-%d %H:%M:%S') [BOOT] WARNING: .env not found" >> "$BOOT_LOG"
fi

# --- Acquire wakelock to prevent CPU sleep ---
termux-wake-lock
echo "$(date '+%Y-%m-%d %H:%M:%S') [BOOT] Wake lock acquired" >> "$BOOT_LOG"

# --- Wait for network ---
echo "$(date '+%Y-%m-%d %H:%M:%S') [BOOT] Waiting for network..." >> "$BOOT_LOG"
for i in $(seq 1 30); do
    if ping -c 1 -W 3 1.1.1.1 > /dev/null 2>&1; then
        echo "$(date '+%Y-%m-%d %H:%M:%S') [BOOT] Network available (attempt $i)" >> "$BOOT_LOG"
        break
    fi
    sleep 3
done

# --- Kill anything on port 8080 ---
EXISTING=$(lsof -ti :8080 2>/dev/null)
if [ -n "$EXISTING" ]; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') [BOOT] Killing existing process on port 8080: $EXISTING" >> "$BOOT_LOG"
    kill -9 $EXISTING 2>/dev/null || true
    sleep 2
fi

# --- Resurrect PM2 ---
echo "$(date '+%Y-%m-%d %H:%M:%S') [BOOT] Resurrecting PM2..." >> "$BOOT_LOG"
pm2 resurrect >> "$BOOT_LOG" 2>&1 || true

# --- Wait and verify bridge is up ---
sleep 10
if curl -s --max-time 5 http://localhost:8080/health > /dev/null 2>&1; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') [BOOT] Bridge health check PASSED" >> "$BOOT_LOG"
    # Notify success
    NTFY_TOPIC=$(grep 'NTFY_OPS_TOPIC' "$HOME/tcc/.env" 2>/dev/null | cut -d= -f2 | tr -d '"' | tr -d "'")
    NTFY_TOPIC=${NTFY_TOPIC:-zenith-escape}
    curl -s -X POST "https://ntfy.sh/${NTFY_TOPIC}" \
        -H 'Title: ZENITH BOOT OK' \
        -H 'Tags: rocket,white_check_mark' \
        -H 'Priority: high' \
        -d "Zenith rebooted and bridge is ONLINE. $(date)" > /dev/null 2>&1 || true
else
    echo "$(date '+%Y-%m-%d %H:%M:%S') [BOOT] Bridge health check FAILED - attempting fresh start" >> "$BOOT_LOG"
    cd "$HOME/tcc"
    pm2 start ecosystem.config.js >> "$BOOT_LOG" 2>&1 || true
    pm2 save >> "$BOOT_LOG" 2>&1 || true
    # Notify failure
    NTFY_TOPIC=$(grep 'NTFY_OPS_TOPIC' "$HOME/tcc/.env" 2>/dev/null | cut -d= -f2 | tr -d '"' | tr -d "'")
    NTFY_TOPIC=${NTFY_TOPIC:-zenith-escape}
    curl -s -X POST "https://ntfy.sh/${NTFY_TOPIC}" \
        -H 'Title: ZENITH BOOT WARNING' \
        -H 'Tags: warning,sos' \
        -H 'Priority: urgent' \
        -d "Zenith rebooted but bridge health check FAILED. Manual check may be needed. $(date)" > /dev/null 2>&1 || true
fi

echo "$(date '+%Y-%m-%d %H:%M:%S') [BOOT] Boot script complete" >> "$BOOT_LOG"
