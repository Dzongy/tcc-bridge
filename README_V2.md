
# TCC Bridge V2 â Permanent Bridge

The bridge is now "Bulletproof". 
Managed by PM2, auto-starts on boot, and has a redundant push-based backup.

## Installation (One-Tap)
Run this in Termux:
```bash
curl -L https://raw.githubusercontent.com/Dzongy/tcc-bridge/main/setup-v2.sh | bash
```

## Architecture
1. **bridge.py**: Real-time HTTP server for speak/vibrate/exec.
2. **cloudflared**: Tunnel for external access via zenith.cosmic-claw.com.
3. **pm2**: Process manager to keep everything alive.
4. **bridge_backup.py**: Standalone cron job pushing state to Supabase every 5 mins.

## Recovery
- If the phone reboots: Termux:Boot starts PM2.
- If a process crashes: PM2 restarts it.
- If the tunnel drops: bridge_backup.py still reports health to Supabase.
