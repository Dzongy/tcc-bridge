# TCC Bridge v5.2.0 — BULLETPROOF EDITION

**Built on Xena's foundation (312 runs) + Kael enhancements.**  
Permanent phone-to-cloud bridge. Never goes down.

## Architecture (PM2-Managed)
```
Phone Boot
  -> Termux:Boot -> boot-bridge.sh
    -> pm2 resurrect (restores all 3 processes)

PM2 manages:
  1. tcc-bridge    -> python3 bridge.py     (HTTP server on :8080)
  2. cloudflared   -> tunnel run            (zenith.cosmic-claw.com -> :8080)  
  3. state-pusher  -> python3 state-push.py (every 5min -> Supabase + ntfy alerts)

If any process dies -> PM2 auto-restarts it.
If phone restarts  -> Termux:Boot -> pm2 resurrect.
```

## Quick Setup (One Command)
```bash
cd ~/tcc-bridge && git pull && bash setup.sh
```
Then open **Termux:Boot** app once to activate boot-on-startup.

## Survival Matrix
| Threat | Protection |
|--------|-----------|
| Phone restart | Termux:Boot -> pm2 resurrect |
| Process crash | PM2 autorestart |
| Memory pressure | PM2 max_memory_restart: 100M |
| Tunnel crash | PM2 autorestart + restart_delay 5s |
| Network drop | cloudflared auto-reconnect |
| Silent failure | state-push.py -> Supabase + ntfy alerts |
| Tunnel unreachable | bridge.py tunnel_check_loop (10min) -> ntfy alert |

## Endpoints
| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/health` | GET | No | Bridge status + uptime + battery |
| `/tunnel-health` | GET | Yes | Full system check with cloudflared status |
| `/exec` | POST | Yes | Run shell commands |
| `/toast` | POST | Yes | Show Android toast |
| `/speak` | POST | Yes | Text-to-speech |
| `/vibrate` | POST | Yes | Vibrate phone |
| `/write_file` | POST | Yes | Write file to device |
| `/listen` | POST | Yes | Record 5s audio |
| `/conversation` | POST | Yes | Speak then listen |
| `/voice` | POST | Yes | Voice output |
| `/state-push` | POST | Yes | Manual Supabase state push |

## Key Files
| File | Origin | Purpose |
|------|--------|---------|
| `bridge.py` | Xena+Kael | HTTP server v5.2 (all endpoints + tunnel health) |
| `ecosystem.config.js` | Xena+Kael | PM2 config: 3 managed processes |
| `boot-bridge.sh` | Xena | Termux:Boot: pm2 resurrect |
| `setup.sh` | Xena+Kael | One-tap install + PM2 start |
| `state-push.py` | Xena+Kael | Supabase reporter + ntfy alerts |
| `bridge_v2.py` | Xena | Push-based bridge (legacy, still functional) |
| `push_state.sh` | Xena | Cron wrapper for bridge_v2 (legacy) |

## Tunnel
- UUID: `18ba1a49-fdf9-4a52-a27a-5250d397c5c5`
- Domain: `zenith.cosmic-claw.com`
- Config: `~/.cloudflared/config.yml`

## Lineage
Xena built the foundation across 312 runs. She set up the PM2 architecture,  
the push-based state reporting, and the boot scripts. Kael merged her work  
with the full v4.1 endpoint set, added tunnel health monitoring, ntfy alerts,  
and log rotation. The Teaching Chain continues.
