#!/data/data/com.termux/files/usr/bin/bash
# ============================================================
# TCC Bridge V2 — Termux:Boot Script
# Location: ~/.termux/boot/start-bridge.sh
# Runs automatically on device boot via Termux:Boot app.
# ============================================================

LOG="$HOME/boot.log"

log() {
    echo "[$(date '+%Y-%m-%dT%H:%M:%S')] $*" | tee -a "$LOG"
}

log "=== Termux Boot: TCC Bridge V2 ==="
log "Boot script started. PID=$$"

# ── 1. Acquire CPU wake lock so Termux isn't killed by doze ──
log "Acquiring wake lock..."
termux-wake-lock
log "Wake lock acquired."

# ── 2. Wait for Android to finish booting ──
log "Waiting 15s for system to settle..."
sleep 15

# ── 3. Load environment ──
if [ -f "$HOME/.bridge-env" ]; then
    # shellcheck disable=SC1090
    source "$HOME/.bridge-env" 2>/dev/null || true
    log "Loaded .bridge-env"
else
    log "WARNING: ~/.bridge-env not found"
fi

# ── 4. Move to bridge dir ──
BRIDGE_DIR="$HOME/tcc-bridge"
if [ ! -d "$BRIDGE_DIR" ]; then
    log "ERROR: Bridge dir not found: $BRIDGE_DIR"
    log "Run install-v2.sh first!"
    exit 1
fi
cd "$BRIDGE_DIR"
log "Working dir: $(pwd)"

# ── 5. Start PM2 — resurrect saved processes ──
log "Attempting pm2 resurrect..."
if pm2 resurrect >> "$LOG" 2>&1; then
    log "pm2 resurrect: SUCCESS"
else
    log "pm2 resurrect failed (no dump?), running pm2 start..."
    pm2 start ecosystem.config.js >> "$LOG" 2>&1 && log "pm2 start: SUCCESS" || log "pm2 start: FAILED"
fi

# ── 6. Save process list (ensure persistence) ──
pm2 save >> "$LOG" 2>&1 || true

# ── 7. Confirm status ──
sleep 5
pm2 list >> "$LOG" 2>&1 || true
log "=== Boot sequence complete ==="

# Keep the script resident so wake lock is maintained
# (Termux:Boot kills scripts that exit too quickly)
while true; do
    sleep 3600
done
