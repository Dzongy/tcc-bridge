# TCC Bridge V2 — Permanent & Bulletproof
One-tap setup for the TCC Bridge on Android (Termux).

## Features
- **Unkillable**: Managed by PM2 + Termux:Boot
- **Cloudflare Tunnel**: Bulletproof connection to zenith.cosmic-claw.com
- **Health Monitoring**: Pushes state to Supabase every 5m
- **Crash Recovery**: Auto-restarts on network or process failure

## Installation (Copy-Paste into Termux)
```bash
cd $HOME && pkg update -y && pkg install -y git && \
rm -rf tcc-bridge && git clone https://github.com/Dzongy/tcc-bridge.git && \
cd tcc-bridge && bash deploy-v2.sh
```

## Commands
- **Check Status**: `pm2 status`
- **Logs**: `pm2 logs bridge`
- **Restart All**: `pm2 restart all`
