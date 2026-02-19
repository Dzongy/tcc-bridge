#!/data/data/com.termux/files/usr/bin/sh
# TCC Bridge v2.0 Setup
# One-command installer

set -e

PROJECT_DIR="/data/data/com.termux/files/home/tcc"
LOG_DIR="${PROJECT_DIR}/.bridge"

echo "== TCC Bridge v2.0 Setup =="
echo ""

# Create directory
mkdir -p "${PROJECT_DIR}"
mkdir -p "$LOG_DIR"

# Install dependencies
echo "[1] Installing dependencies..."
pip3 install requests -q

# Download files
echo "[2] Downloading bridge files..."
curl -sS "https://raw.githubusercontent.com/Dzongy/tcc-bridge/main/bridge_v2.py" -o "${PROJECT_DIR}/bridge_v2.py"
curl -sS "https://raw.githubusercontent.com/Dzongy/tcc-bridge/main/push_state.sh" -o "${PROJECT_DIR}/push_state.sh"
curl -sS "https://raw.githubusercontent.com/Dzongy/tcc-bridge/main/bridge.py" -o "${PROJECT_DIR}/bridge.py"

chmod +x "${PROJECT_DIR}/push_state.sh"

# Setup cron job
echo "[3] Setting up cron job..."
echo "* * * * * ${PROJECT_DIR}/push_state.sh" | crontab -

# Test connectivity
echo "[4] Testing connectivity..."
cd "$PROJECT_DIR"
python3 bridge_v2.py --once
if [ $? -eq 0 ]; then
    echo "[OK] Bridge connected successfully!"
else
    echo "[WARN] Bridge test failed. Check configuration."
fi

# Start crond
echo "[5] Starting crond daemon..."
crond

echo ""
echo "== Setup Complete =="
echo "Bridge will push state every 5 minutes."
echo "Logs: ${LOG_DIR}/bridge.log"
echo ""
