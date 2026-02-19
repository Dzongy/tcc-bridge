# TCC Bridge V2 - Permanent Mobile Sovereignty
Bulletproof bridge infrastructure for Termux.

## 🚀 One-Tap Setup
```bash
curl -sS https://raw.githubusercontent.com/Dzongy/tcc-bridge/main/deploy-v2.sh | bash
```

## 🏗️ Components
- **amos.js** (:8765): Node.js entry point & proxy.
- **bridge.py** (:8080): Core command server.
- **state-push.py**: Periodic Supabase heartbeats.
- **watchdog-v2.sh**: Health guardian.
- **boot-bridge.sh**: Termux:Boot integration.

## 📊 Monitoring
Health: [zenith.cosmic-claw.com/health](https://zenith.cosmic-claw.com/health)
Alerts: ntfy.sh/tcc-zenith-hive
