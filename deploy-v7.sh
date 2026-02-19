#!/data/data/com.termux/files/usr/bin/bash
# TCC Bridge V7.0 Deploy Script
# Run this once to deploy the latest bridge from GitHub

set -e

echo "=== TCC BRIDGE V7.0 DEPLOY ==="
echo "Timestamp: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"

# Navigate to bridge directory
cd ~/tcc-bridge

# Pull latest from GitHub
echo "Pulling latest from GitHub..."
git fetch origin main
git reset --hard origin/main

# Set environment variables for PM2
echo "Setting PM2 environment variables..."
export BRIDGE_PORT=8765
export BRIDGE_AUTH="amos-bridge-2026"
export NTFY_TOPIC="tcc-zenith-hive"
export SUPABASE_URL="https://vbqbbziqleymxcyesmky.supabase.co"
export SUPABASE_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZicWJiemlxbGV5bXhjeWVzbWt5Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3MTExMTUxNiwiZXhwIjoyMDg2Njg3NTE2fQ.MREdeLv0R__fHe61lOYSconedoo_qHItZUpmcR-IORQ"
export DEVICE_ID="zenith-phone"
export TUNNEL_URL="https://zenith.cosmic-claw.com"

# Create PM2 ecosystem file
cat > ecosystem.config.js << 'ECOEOF'
module.exports = {
  apps: [
    {
      name: "tcc-bridge",
      script: "bridge.py",
      interpreter: "python3",
      cwd: "/data/data/com.termux/files/home/tcc-bridge",
      env: {
        BRIDGE_PORT: "8765",
        BRIDGE_AUTH: "amos-bridge-2026",
        NTFY_TOPIC: "tcc-zenith-hive",
        SUPABASE_URL: "https://vbqbbziqleymxcyesmky.supabase.co",
        SUPABASE_KEY: "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZicWJiemlxbGV5bXhjeWVzbWt5Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3MTExMTUxNiwiZXhwIjoyMDg2Njg3NTE2fQ.MREdeLv0R__fHe61lOYSconedoo_qHItZUpmcR-IORQ",
        DEVICE_ID: "zenith-phone",
        TUNNEL_URL: "https://zenith.cosmic-claw.com"
      },
      max_restarts: 100,
      restart_delay: 2000,
      autorestart: true
    }
  ]
};
ECOEOF

# Restart bridge with new code
echo "Restarting bridge..."
pm2 delete tcc-bridge 2>/dev/null || true
pm2 start ecosystem.config.js
pm2 save

echo ""
echo "=== DEPLOY COMPLETE ==="
echo "Bridge V7.0 running on port 8765"
echo "Test: curl http://127.0.0.1:8765/health"
pm2 list
