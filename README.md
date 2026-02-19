# TCC Bridge v5.0 — BULLETPROOF EDITION

**Permanent phone-to-cloud bridge. Never goes down.**

## What It Does
Runs on Termux (Android), exposes HTTP endpoints for remote phone control via Cloudflare tunnel at `zenith.cosmic-claw.com`.

## Survival Features
| Threat | Protection |
|--------|-----------|
| Phone restart | Termux:Boot auto-start |
| Termux killed | Watchdog auto-restart |
| Bridge crash | Watchdog + exponential backoff |
| Tunnel crash | Health monitor + cloudflared auto-restart |
| Network drop | Cloudflared auto-reconnect |
| Android OOM | Watchdog detects and restarts |
| Silent failure | Cron state push to Supabase + ntfy alerts |

## Quick Setup (One Command)
```bash
cd ~/tcc-bridge && git pull && bash deploy-v2.sh
```

Then open the **Termux:Boot** app once (just open it — activates boot-on-startup).

## Endpoints
| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/health` | GET | No | Bridge status + uptime |
| `/tunnel-health` | GET | Yes | Full system check |
| `/exec` | POST | Yes | Run shell commands |
| `/toast` | POST | Yes | Show Android toast |
| `/speak` | POST | Yes | Text-to-speech |
| `/vibrate` | POST | Yes | Vibrate phone |
| `/write_file` | POST | Yes | Write file to device |
| `/listen` | POST | Yes | Record audio |
| `/conversation` | POST | Yes | Speak + listen |
| `/voice` | POST | Yes | Voice output |
| `/state-push` | POST | Yes | Manual Supabase push |

## Files
| File | Purpose |
|------|---------|
| `bridge.py` | Main HTTP server (v5.0) |
| `deploy-v2.sh` | One-tap permanent setup |
| `boot-bridge.sh` | Termux:Boot auto-start |
| `watchdog-v2.sh` | Process watchdog with backoff |
| `state-push.py` | Cron-based health reporter |
| `ecosystem.config.js` | PM2 config (optional) |

## Architecture
```
Phone Restart
  -> Termux:Boot -> boot-bridge.sh
      -> watchdog-v2.sh (loop forever)
          -> bridge.py (HTTP server on :8080)
      -> cloudflared tunnel (zenith.cosmic-claw.com -> :8080)
      -> crond -> state-push.py (every 5min -> Supabase + ntfy)
```

## Tunnel
- UUID: `18ba1a49-fdf9-4a52-a27a-5250d397c5c5`
- Domain: `zenith.cosmic-claw.com`
- Config: `~/.cloudflared/config.yml`
