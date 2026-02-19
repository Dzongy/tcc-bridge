#!/data/data/com.termux/files/usr/bin/bash
# ╔══════════════════════════════════════════════════════╗
# ║   TCC BRIDGE V2 — TERMUX:BOOT LAUNCHER              ║
# ║   Place in: ~/.termux/boot/start_tcc.sh             ║
# ║   Make executable: chmod +x ~/.termux/boot/start_tcc.sh
# ╚══════════════════════════════════════════════════════╝

# ─── PATHS ────────────────────────────────────────────────────────────────────
export PATH="$PATH:/data/data/com.termux/files/usr/bin:/data/data/com.termux/files/usr/bin/applets"
export HOME="/data/data/com.termux/files/home"
export PREFIX="/data/data/com.termux/files/usr"

# Source bash profile if it exists
[ -f "$HOME/.bashrc"  ] && source "$HOME/.bashrc"  2>/dev/null || true
[ -f "$HOME/.profile" ] && source "$HOME/.profile" 2>/dev/null || true

# ─── CONSTANTS ────────────────────────────────────────────────────────────────
BRIDGE_DIR="$HOME/tcc-bridge"
LOG_DIR="$HOME/logs"
BOOT_LOG="$LOG_DIR/boot.log"
CFD_TUNNEL_UUID="18ba1a49-fdf9-4a52-a27a-5250d397c5c5"
CFD_CONFIG="$HOME/.cloudflared/config.yml"
NTFY_HIVE="tcc-zenith-hive"
DEVICE_ID="$(hostname 2>/dev/null || echo 'termux')"

# ─── SETUP ────────────────────────────────────────────────────────────────────
mkdir -p "$LOG_DIR"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$BOOT_LOG"
}

log "=== TCC Bridge V2 Boot Sequence START ==="
log "Device: $DEVICE_ID"
log "Bridge Dir: $BRIDGE_DIR"

# ─── WAIT FOR SYSTEM ──────────────────────────────────────────────────────────
log "Waiting 15s for system to stabilise..."
sleep 15

# ─── WAKELOCK ─────────────────────────────────────────────────────────────────
log "Acquiring wakelock..."
termux-wake-lock 2>/dev/null && log "Wakelock acquired." || log "WARN: wakelock failed."

# ─── WAIT FOR NETWORK ─────────────────────────────────────────────────────────
log "Waiting for network..."
MAX_WAIT=60
WAIT=0
while ! ping -c1 -W2 8.8.8.8 &>/dev/null 2>&1; do
    sleep 5
    WAIT=$((WAIT + 5))
    if [ $WAIT -ge $MAX_WAIT ]; then
        log "WARN: Network not available after ${MAX_WAIT}s — proceeding anyway."
        break
    fi
done
log "Network check done (waited ${WAIT}s)."

# ─── START CROND ──────────────────────────────────────────────────────────────
if command -v crond &>/dev/null; then
    if ! pgrep -x crond &>/dev/null; then
        crond 2>/dev/null && log "crond started." || log "WARN: crond failed to start."
    else
        log "crond already running."
    fi
fi

# ─── VALIDATE BRIDGE DIR ──────────────────────────────────────────────────────
if [ ! -d "$BRIDGE_DIR" ]; then
    log "ERROR: Bridge directory not found: $BRIDGE_DIR"
    log "Run install_v2.sh first!"
    exit 1
fi

# ─── START PM2 ECOSYSTEM ──────────────────────────────────────────────────────
cd "$BRIDGE_DIR" || exit 1

# Check if PM2 already has processes running
if pm2 list 2>/dev/null | grep -qE "(online|launching)"; then
    log "PM2 already has running processes — restarting all."
    pm2 restart all >> "$BOOT_LOG" 2>&1 && log "PM2 restart all OK." || log "WARN: PM2 restart had errors."
else
    log "Starting PM2 ecosystem..."
    pm2 start ecosystem.config.js >> "$BOOT_LOG" 2>&1 \
        && log "PM2 ecosystem started OK." \
        || log "ERROR: PM2 ecosystem failed to start!"
fi

# Save PM2 process list
pm2 save >> "$BOOT_LOG" 2>&1 || log "WARN: pm2 save failed."

# ─── WAIT & VERIFY ────────────────────────────────────────────────────────────
log "Waiting 10s for bridge to come up..."
sleep 10

if curl -sf --max-time 5 http://localhost:8765/health | grep -q "online" 2>/dev/null; then
    log "SUCCESS: Bridge is UP on localhost:8765."
    BRIDGE_STATUS="online"
else
    log "WARN: Bridge health check failed after boot."
    BRIDGE_STATUS="down"
    # Attempt one recovery restart
    log "Attempting recovery restart of tcc-bridge..."
    pm2 restart tcc-bridge >> "$BOOT_LOG" 2>&1 || true
fi

# ─── NTFY BOOT ALERT ──────────────────────────────────────────────────────────
curl -s -X POST "https://ntfy.sh/${NTFY_HIVE}" \
    -H "Title: TCC Bridge V2 Boot" \
    -H "Tags: rocket,robot" \
    -H "Priority: default" \
    -d "${DEVICE_ID}: Boot complete. Bridge=${BRIDGE_STATUS}. Tunnel=starting." \
    >> "$BOOT_LOG" 2>&1 || true

# ─── PM2 STATUS LOG ───────────────────────────────────────────────────────────
pm2 list >> "$BOOT_LOG" 2>&1 || true

log "=== TCC Bridge V2 Boot Sequence COMPLETE ==="
