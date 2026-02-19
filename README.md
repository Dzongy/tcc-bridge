# TCC Bridge V2 â KAEL ULTRA (BULLETPROOF)

Built for Commander by KAEL God Builder.

## Features
- **Permanent**: Survives phone restart, network drops, and Android memory cleanup.
- **Bulletproof**: PM2 process management + Watchdog monitor.
- **State Pulse**: Periodic heartbeats to Supabase showing battery and network health.
- **One-Tap Setup**: Simple command to install and start everything.

## Installation (One-Tap)
Run this command in Termux:
```bash
curl -sS https://raw.githubusercontent.com/Dzongy/tcc-bridge/main/deploy-v2.sh | bash
```

## Components
- **bridge.py**: The core API bridge (V6.2.0).
- **state-push.py**: Background state pusher for Supabase.
- **ecosystem.config.js**: PM2 configuration.
- **watchdog-v2.sh**: Health check loop.
- **boot-bridge.sh**: Termux:Boot startup script.

## Monitoring
- **Health**: check `zenith.cosmic-claw.com/health`
- **Hive**: Alerts sent to ntfy.sh/tcc-zenith-hive
