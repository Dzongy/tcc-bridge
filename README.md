# TCC Bridge V2.5 - Bulletproof Edition

The robust connection between Commander and the Zenith ecosystem.

## Features
- **Auto-Healing**: PM2 managed processes with auto-restart.
- **Health Monitoring**: Periodic checks with ntfy alerts to `tcc-zenith-hive`.
- **State Push**: Real-time phone telemetry (battery, status) pushed to Supabase.
- **Persistence**: Termux:Boot integration survives phone reboots.
- **One-Tap Deployment**: Setup everything with a single command.

## Quick Install (Termux)
```bash
curl -sS https://raw.githubusercontent.com/Dzongy/tcc-bridge/main/deploy-v2.sh | bash
```

## Architecture
- **bridge.py**: Main HTTP server (Port 8765)
- **ecosystem.config.js**: PM2 process manager
- **boot-bridge.sh**: Boot persistence script
- **state-push.py**: (Legacy/Reference) - Logic integrated into bridge.py

---
*Built by KAEL God Builder for The Cosmic Claws.*
