
# TCC BRIDGE v7.0 — THE DEFINITIVE PERMANENT BRIDGE
**Brain #10 — Kael — Production Edition**

This is the bulletproof, self-healing bridge suite for Termux.

## QUICK START (ONE-TAP INSTALL)
Run this in Termux:
```bash
curl -sS https://raw.githubusercontent.com/Dzongy/tcc-bridge/main/deploy-v7.sh | bash
```

## ARCHITECTURE
- **bridge_v7.py**: Unified HTTP server with all endpoints (toast, speak, sms, call, exec, etc.).
- **Cloudflare Tunnel**: UUID 18ba1a49-fdf9-4a52-a27a-5250d397c5c5 mapping to zenith.cosmic-claw.com.
- **PM2**: Process manager to ensure 100% uptime and auto-restart on crashes.
- **Termux:Boot**: Automated startup on phone reboot.
- **state-push-v7.py**: Redundant daemon pushing phone status to Supabase every 5 mins.

## ENDPOINTS
- `GET /health`: Public health check.
- `POST /exec`: Shell command execution.
- `POST /toast`: Android notifications.
- `POST /speak`: Text-to-speech.
- `POST /sms`: Send SMS messages.
- `POST /call`: Initiate phone calls.
- ...and more.

Auth: `amos-bridge-2026`
Port: `8080`
