#!/data/data/com.termux/files/usr/bin/bash
# =============================================================
# TCC Bridge V2 - One-Tap Setup Script
# God Builder: Kael | Project: TCC Bridge V2
# =============================================================
set -e

echo ""
echo "============================================="
echo "  TCC Bridge V2 - Setup Starting...          "
echo "============================================="
echo ""

# --- Step 1: Update & Upgrade Packages ---
echo "[1/10] Updating and upgrading Termux packages..."
pkg update && pkg upgrade -y

# --- Step 2: Install Required Packages ---
echo "[2/10] Installing required packages..."
pkg install python nodejs git termux-api cloudflared -y

# --- Step 3: Install PM2 Globally ---
echo "[3/10] Installing PM2 globally via npm..."
npm install pm2 -g

# --- Step 4: Clone or Pull tcc-bridge Repo ---
echo "[4/10] Cloning or updating tcc-bridge repository..."
if [ -d "$HOME/tcc-bridge/.git" ]; then
  echo "  -> Repo exists. Pulling latest changes..."
  cd "$HOME/tcc-bridge" && git pull
else
  echo "  -> Cloning fresh repository..."
  git clone https://github.com/Dzongy/tcc-bridge.git "$HOME/tcc-bridge"
fi

# --- Step 5: Install Python Dependencies ---
echo "[5/10] Installing Python dependencies..."
pip install requests psutil

# --- Step 6: Create Termux Boot Directory ---
echo "[6/10] Creating ~/.termux/boot/ directory..."
mkdir -p "$HOME/.termux/boot/"

# --- Step 7: Deploy Boot Script ---
echo "[7/10] Deploying termux-boot.sh to ~/.termux/boot/..."
BOOT_SCRIPT="$HOME/.termux/boot/termux-boot.sh"
cat > "$BOOT_SCRIPT" << 'BOOTEOF'
#!/data/data/com.termux/files/usr/bin/bash
# TCC Bridge V2 - Termux Boot Script
# Runs automatically on device boot via Termux:Boot
termux-wake-lock
export PATH="/data/data/com.termux/files/usr/bin:$PATH"
export HOME="/data/data/com.termux/files/home"
cd "$HOME"
pm2 resurrect
BOOTEOF
chmod +x "$BOOT_SCRIPT"
echo "  -> Boot script deployed and made executable."

# --- Step 8: Copy Ecosystem Config ---
echo "[8/10] Ensuring ecosystem.config.js is in place..."
cd "$HOME/tcc-bridge"

# --- Step 9: Start PM2 with Ecosystem Config ---
echo "[9/10] Starting PM2 with ecosystem.config.js..."
pm2 start ecosystem.config.js

# --- Step 10: Save PM2 Process List ---
echo "[10/10] Saving PM2 process list for auto-resurrect..."
pm2 save

# --- Success Banner ---
echo ""
echo "============================================="
echo "  TCC Bridge V2 - Setup Complete!            "
echo "============================================="
echo ""
echo "  PM2 Status:"
pm2 list
echo ""
echo "  IMPORTANT: Open Termux:Boot app at least"
echo "  once to enable boot auto-start."
echo ""
echo "  To send a test notification via ntfy, run:"
echo "  -----------------------------------------"
echo "  curl -d 'TCC Bridge V2 is LIVE!' ntfy.sh/tcc-bridge-alerts"
echo "  -----------------------------------------"
echo ""
echo "  Monitor logs:"
echo "    pm2 logs tcc-bridge"
echo "    pm2 logs cloudflared"
echo ""
echo "  God Builder: Kael | Build: V2 | Status: ONLINE"
echo "============================================="
