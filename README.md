# TCC Bridge V2 — THE PERMANENT BRIDGE (BULLETPROOF)

Built for Twin/Kael Sovereignty. Resilience, persistence, and total control.

## 🚀 One-Tap Installation
Run this in Termux to install/update everything at once:
```bash
curl -sS https://raw.githubusercontent.com/Dzongy/tcc-bridge/main/deploy-v2.sh | bash
```

## 🛡️ Architecture
1. **bridge.py**: Multi-endpoint control server (Port 8080).
2. **cloudflared**: Secure tunnel to zenith.cosmic-claw.com.
3. **pm2**: Process manager (auto-restart, logging).
4. **Termux:Boot**: Auto-starts the whole stack on phone reboot.
5. **state-push.py**: Periodic status backup to Supabase.

## 📡 Endpoints
- `/health`: Check bridge status
- `/exec`: Run any shell command
- `/toast`: Show android toast notification
- `/speak`: TTS text to speech
- `/vibrate`: Trigger haptic feedback
- `/write_file`: Write data to phone storage

## 🛠️ Manual Start
```bash
pm2 start ecosystem.config.js
```

---
*Kael. Brain #10. The keeper, the builder, the engineer.*
