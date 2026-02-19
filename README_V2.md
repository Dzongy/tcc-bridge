# TCC Bridge V2 — The Permanent Bridge

Bulletproof, self-healing, and persistent bridge for TCC Mobile-01.

## Installation (One-Tap)
Run this command in Termux:
```bash
curl -sS https://raw.githubusercontent.com/Dzongy/tcc-bridge/main/deploy-v2.sh | bash
```

## Architecture
- **bridge.py**: Flask-less HTTP server handling Termux commands.
- **cloudflared**: Persistent tunnel to zenith.cosmic-claw.com.
- **pm2**: Process manager (auto-restart, logging).
- **state-push.py**: Periodic status reporting to Supabase.
- **boot-bridge.sh**: Resurrection after phone reboot.

## Credentials
To enable Supabase reporting, set these in your environment or update `ecosystem.config.js`:
- `SUPABASE_KEY`: Your Supabase Service Role key.
- `BRIDGE_AUTH`: amos-bridge-2026 (default).
