#!/data/data/com.termux/files/usr/bin/bash
# =============================================================================
# TCC Bridge V2 - Termux Boot Script
# Place this file at: ~/.termux/boot/termux-boot.sh
# chmod +x ~/.termux/boot/termux-boot.sh
# Requires: Termux:Boot app installed from F-Droid
# Tunnel UUID: 18ba1a49-fdf9-4a52-a27a-5250d397c5c5
# =============================================================================

# --- Environment Setup ---
export PATH="/data/data/com.termux/files/home/bin:/data/data/com.termux/files/usr/bin:/data/data/com.termux/files/usr/local/bin:$PATH"
export HOME="/data/data/com.termux/files/home"
export TCC_DIR="$HOME/tcc"
export LOG_FILE="$TCC_DIR/logs/boot.log"

mkdir -p "$TCC_DIR/logs"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log '=== TCC Bridge V2 Boot Sequence Starting ==='
log "PATH: $PATH"
log "Waiting 20s for system and network to stabilise..."

# Wait for Android to fully boot and network to come up
sleep 20

# --- Load Environment Variables ---
if [ -f "$TCC_DIR/.env" ]; then
    log 'Loading .env file...'
    set -a
    # shellcheck disable=SC1090
    source "$TCC_DIR/.env" 2>/dev/null || log 'WARN: .env source had errors'
    set +a
    log '.env loaded.'
else
    log 'WARN: No .env file found at ~/tcc/.env'
fi

# --- Verify PM2 is available ---
if ! command -v pm2 &>/dev/null; then
    log 'ERROR: pm2 not found in PATH. Cannot start bridge.'
    # Attempt ntfy notification if curl is available
    curl -s -d 'TCC Bridge boot FAILED: pm2 not found on device.' \
        "https://ntfy.sh/${NTFY_OPS_TOPIC:-zenith-escape}" \
        -H 'Title: TCC Boot Failure' \
        -H 'Priority: urgent' \
        -H 'Tags: warning,skull' 2>/dev/null || true
    exit 1
fi

log "pm2 found at: $(command -v pm2)"

# --- Attempt PM2 Resurrect (saved process list) ---
log 'Attempting pm2 resurrect from saved dump...'
if pm2 resurrect >> "$LOG_FILE" 2>&1; then
    log 'pm2 resurrect successful.'
else
    log 'pm2 resurrect failed or no dump found. Starting ecosystem directly...'
    if [ -f "$TCC_DIR/ecosystem.config.js" ]; then
        pm2 start "$TCC_DIR/ecosystem.config.js" >> "$LOG_FILE" 2>&1 && \
            log 'PM2 ecosystem started from config.' || \
            log 'ERROR: PM2 ecosystem start failed!'
    else
        log 'ERROR: ecosystem.config.js not found at ~/tcc/ecosystem.config.js'
        curl -s -d 'TCC Bridge boot FAILED: ecosystem.config.js missing.' \
            "https://ntfy.sh/${NTFY_OPS_TOPIC:-zenith-escape}" \
            -H 'Title: TCC Boot Failure' \
            -H 'Priority: urgent' \
            -H 'Tags: warning' 2>/dev/null || true
        exit 1
    fi
fi

# --- Verify tcc-tunnel (cloudflared) is running via PM2 ---
sleep 5
TUNNEL_STATUS=$(pm2 jlist 2>/dev/null | python3 -c "
import sys, json
try:
    procs = json.load(sys.stdin)
    t = next((p for p in procs if p.get('name') == 'tcc-tunnel'), None)
    print(t['pm2_env']['status'] if t else 'not_found')
except:
    print('parse_error')
" 2>/dev/null || echo 'unknown')

log "tcc-tunnel PM2 status: $TUNNEL_STATUS"

if [ "$TUNNEL_STATUS" != 'online' ]; then
    log "WARN: tcc-tunnel is '$TUNNEL_STATUS'. Attempting standalone cloudflared start..."
    CLOUDFLARED_BIN="$HOME/bin/cloudflared"
    CF_CONFIG="$HOME/.cloudflared/config.yml"

    if [ -x "$CLOUDFLARED_BIN" ]; then
        # Check if cloudflared is already running outside PM2
        if ! pgrep -f 'cloudflared tunnel' > /dev/null 2>&1; then
            log 'Starting cloudflared standalone with tunnel UUID...'
            nohup "$CLOUDFLARED_BIN" tunnel run \
                --token '18ba1a49-fdf9-4a52-a27a-5250d397c5c5' \
                >> "$TCC_DIR/logs/tunnel-standalone.log" 2>&1 &
            log "cloudflared started standalone (PID: $!)"
        else
            log 'cloudflared process already running outside PM2.'
        fi
    else
        log 'WARN: cloudflared binary not found at ~/bin/cloudflared'
    fi
else
    log 'tcc-tunnel is online via PM2. Good.'
fi

# --- Save PM2 process list for next boot ---
pm2 save >> "$LOG_FILE" 2>&1 && log 'pm2 save complete.' || log 'WARN: pm2 save failed.'

# --- Final Status Report ---
BRIDGE_STATUS=$(pm2 jlist 2>/dev/null | python3 -c "
import sys, json
try:
    procs = json.load(sys.stdin)
    b = next((p for p in procs if p.get('name') == 'tcc-bridge'), None)
    print(b['pm2_env']['status'] if b else 'not_found')
except:
    print('unknown')
" 2>/dev/null || echo 'unknown')

log "tcc-bridge status: $BRIDGE_STATUS"
log "tcc-tunnel status: $TUNNEL_STATUS"

# --- Send boot notification via ntfy ---
curl -s \
    -d "TCC Bridge V2 booted. Bridge: $BRIDGE_STATUS | Tunnel: $TUNNEL_STATUS | $(date)" \
    "https://ntfy.sh/${NTFY_OPS_TOPIC:-zenith-escape}" \
    -H 'Title: TCC Bridge Boot' \
    -H 'Priority: default' \
    -H 'Tags: white_check_mark,satellite' 2>/dev/null || log 'WARN: ntfy notification failed (network may not be ready yet).'

log '=== TCC Bridge V2 Boot Sequence Complete ==='
exit 0
