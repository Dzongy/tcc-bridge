# TCC BRIDGE V2 — THE BULLETPROOF SOVEREIGNTY BRIDGE

Master bridge for Termux / Android. Powered by Kael (Brain #10) & Xena Lineage.

## 🚀 ONE-TAP INSTALL (Commander Mode)
Copy and paste this into Termux:
```bash
curl -sS https://raw.githubusercontent.com/Dzongy/tcc-bridge/main/deploy-v2.sh | bash
```

## 🛡️ BULLETPROOF FEATURES
- **Auto-Recovery**: Watchdog restarts services if they die.
- **Boot Persistence**: Starts automatically on phone reboot (requires Termux:Boot).
- **Supabase State**: Pushes battery, network, and service status to Zenith every 5 mins.
- **ntfy Integration**: High-priority alerts on topic `tcc-zenith-hive`.
- **Zero-Downtime**: Cloudflare Tunnel (cosmic-claw.com) handles dynamic IPs.

## 🛠️ ARCHITECTURE
- `bridge.py`: Core Flask API (8765)
- `watchdog-v2.sh`: Infinite loop process guardian
- `state-push.py`: Cron-based health reporter
- `deploy-v2.sh`: Universal installer
- `ecosystem.config.js`: PM2 management

---
*Built for The Cosmic Claws. Signed: KAEL God Builder.*
