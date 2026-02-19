# TCC Bridge V2 — Bulletproof Edition
The definitive permanent bridge for the TCC Sovereignty project.

## One-Tap Setup
Run this command in Termux to install and start everything:
```bash
curl -sS https://raw.githubusercontent.com/Dzongy/tcc-bridge/main/deploy-v2.sh | bash
```

## Features
- Auto-start on boot (via Termux:Boot)
- PM2 process management (auto-restart on crash)
- Periodic state push to Supabase
- Cloudflare Tunnel integration
- Health monitoring via ntfy
