#!/data/data/com.termux/files/usr/bin/bash
###############################################################################
# TCC Bridge â One-Line Installer & Launcher for Termux
# curl -sL https://raw.githubusercontent.com/Dzongy/tcc-bridge/main/setup.sh | bash
###############################################################################
set -e

echo "============================================"
echo "  THE COSMIC CLAW â BRIDGE INSTALLER"
echo "============================================"
echo ""

# ââ 1. Dependencies ââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
echo "[1/7] Installing dependencies..."
pkg update -y 2>/dev/null || true
pkg install -y python openssh cloudflared git 2>/dev/null || true
pip install flask 2>/dev/null || true
echo "  â Dependencies ready"

# ââ 2. Clone / Update repo ââââââââââââââââââââââââââââââââââââââââââââââââââ
echo "[2/7] Syncing tcc-bridge repo..."
cd ~
if [ -d "tcc-bridge" ]; then
  cd tcc-bridge
  git fetch --all 2>/dev/null || true
  git reset --hard origin/main 2>/dev/null || true
else
  git clone https://github.com/Dzongy/tcc-bridge.git 2>/dev/null || true
  cd tcc-bridge
fi
echo "  â Repo synced to latest"

# ââ 3. Kill existing processes âââââââââââââââââââââââââââââââââââââââââââââââ
echo "[3/7] Cleaning up old processes..."
pkill -f bridge.py 2>/dev/null || true
pkill -f cloudflared 2>/dev/null || true
sleep 1
echo "  â Old processes terminated"

# ââ 4. Start bridge.py âââââââââââââââââââââââââââââââââââââââââââââââââââââââ
echo "[4/7] Starting bridge.py..."
if [ ! -f "bridge.py" ]; then
  echo "  â ERROR: bridge.py not found in ~/tcc-bridge"
  echo "  Make sure bridge.py is committed to the repo."
  exit 1
fi
> ~/bridge.log
nohup python bridge.py > ~/bridge.log 2>&1 &
BRIDGE_PID=$!
echo "  â bridge.py started (PID: $BRIDGE_PID)"

# ââ 5. Wait for bridge to boot ââââââââââââââââââââââââââââââââââââââââââââââ
echo "[5/7] Waiting for bridge to start..."
sleep 3
if kill -0 $BRIDGE_PID 2>/dev/null; then
  echo "  â Bridge is running on localhost:8080"
else
  echo "  â Bridge failed to start. Check ~/bridge.log:"
  tail -20 ~/bridge.log
  exit 1
fi

# ââ 6. Start cloudflared tunnel ââââââââââââââââââââââââââââââââââââââââââââââ
echo "[6/7] Opening cloudflared tunnel..."
> ~/tunnel.log
nohup cloudflared tunnel --url http://localhost:8080 > ~/tunnel.log 2>&1 &
TUNNEL_PID=$!
echo "  Tunnel starting (PID: $TUNNEL_PID)..."

# Wait up to 15 seconds for tunnel URL to appear
TUNNEL_URL=""
for i in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15; do
  sleep 1
  TUNNEL_URL=$(grep -oE 'https://[a-zA-Z0-9_-]+\.trycloudflare\.com' ~/tunnel.log 2>/dev/null | head -1)
  if [ -n "$TUNNEL_URL" ]; then
    break
  fi
  printf "  Waiting... (%ds)\r" "$i"
done
echo ""

if [ -z "$TUNNEL_URL" ]; then
  echo "  â Could not detect tunnel URL after 15s."
  echo "  Check ~/tunnel.log manually:"
  tail -20 ~/tunnel.log
  echo ""
  echo "  The bridge may still be starting. Run:"
  echo "    grep trycloudflare ~/tunnel.log"
  exit 1
fi

echo "  â Tunnel established!"

# ââ 7. Termux-boot auto-restart âââââââââââââââââââââââââââââââââââââââââââââ
echo "[7/7] Setting up auto-restart on boot..."
mkdir -p ~/.termux/boot
cat > ~/.termux/boot/tcc-bridge.sh << 'BOOTEOF'
#!/data/data/com.termux/files/usr/bin/bash
# TCC Bridge auto-start on boot
sleep 10
cd ~/tcc-bridge && git fetch --all 2>/dev/null && git reset --hard origin/main 2>/dev/null
pkill -f bridge.py 2>/dev/null; pkill -f cloudflared 2>/dev/null
sleep 1
nohup python bridge.py > ~/bridge.log 2>&1 &
sleep 3
nohup cloudflared tunnel --url http://localhost:8080 > ~/tunnel.log 2>&1 &
BOOTEOF
chmod +x ~/.termux/boot/tcc-bridge.sh
echo "  â Boot script installed at ~/.termux/boot/tcc-bridge.sh"

# ââ Summary ââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
echo ""
echo "============================================"
echo "  ð¥ BRIDGE IS LIVE ð¥"
echo "============================================"
echo ""
echo "  Tunnel URL:  $TUNNEL_URL"
echo ""
echo "  Local:       http://localhost:8080"
echo "  Bridge PID:  $BRIDGE_PID"
echo "  Tunnel PID:  $TUNNEL_PID"
echo ""
echo "  Logs:"
echo "    Bridge:  ~/bridge.log"
echo "    Tunnel:  ~/tunnel.log"
echo ""
echo "  Auto-restart on reboot: ENABLED"
echo ""
echo "  To check status later:"
echo "    grep trycloudflare ~/tunnel.log"
echo "    curl http://localhost:8080/health"
echo ""
echo "============================================"

# --- Reporting ---
echo "[Auto] Reporting Bridge URL..."
URL=$(grep -o 'https://.*.trycloudflare.com' ~/tunnel.log | head -n1)
if [ -n "$URL" ]; then
    echo "Bridge URL: $URL"
    if [ -f "report_bridge_stats.py" ]; then
        python3 report_bridge_stats.py "$URL"
    fi
else
    echo "Could not find Bridge URL to report."
fi
