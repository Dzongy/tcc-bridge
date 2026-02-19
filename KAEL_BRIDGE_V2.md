# KAEL BRIDGE V2 — SOVEREIGN BULLETPROOF EDITION

This setup is designed for 100% uptime on Android (Termux).

## Components
1. **bridge.py (v5.3.0)**: Advanced multi-endpoint bridge with Supabase sync and ntfy alerts.
2. **ecosystem.config.js**: PM2 configuration that manages the Bridge, the Cloudflare Tunnel, and the Watchdog.
3. **watchdog.sh**: Active monitor that checks localhost:8080/health every 5 mins. If the bridge is stuck, it restarts PM2.
4. **boot-bridge.sh**: Termux:Boot script to auto-start everything on phone reboot.

## How to Install / Update
Run this one-tap command in Termux:
```bash
curl -sS https://raw.githubusercontent.com/Dzongy/tcc-bridge/main/deploy-v2.sh | bash
```

## Monitoring
- **ntfy**: Subscribe to topic `tcc-zenith-hive` for real-time status and alerts.
- **Supabase**: Device state is pushed to the `kael_memory` table.
