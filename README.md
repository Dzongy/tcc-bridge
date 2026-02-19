# TCC BRIDGE V2 (v5.0.0) — Sovereignty Edition
Bulletproof, permanent, never goes down.

## Features
- **Auto-Start:** Starts on phone reboot via Termux:Boot.
- **Process Management:** Managed by PM2 with auto-restart.
- **Watchdog:** Bash-level guardian for double redundancy.
- **Health Checks:** Heartbeat every 5 minutes to ntfy.
- **State Monitoring:** Real-time battery/wifi status via termux-api.

## One-Tap Install
Run this in Termux:
```bash
curl -sS https://raw.githubusercontent.com/Dzongy/tcc-bridge/main/deploy-v2.sh | bash
```

## Component List
- `bridge.py`: The core Python bridge server.
- `deploy-v2.sh`: The master setup script.
- `boot-bridge.sh`: The boot-time loader.
- `watchdog-v2.sh`: The process guardian.
- `state-push.py`: Heartbeat script.
- `ecosystem.config.js`: PM2 configuration.
