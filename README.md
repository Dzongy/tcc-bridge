# TCC Bridge V2 - Bulletproof Sovereignty
This repository contains the core bridge infrastructure for Termux-based mobile sovereignty.

## One-Tap Installation
Run this command in Termux to install or upgrade everything:
```bash
curl -sS https://raw.githubusercontent.com/Dzongy/tcc-bridge/main/deploy-v2.sh | bash
```

## Infrastructure Components
1. **bridge.py**: Python server handling commands and state pushing.
2. **watchdog-v2.sh**: Infinite loop process guardian.
3. **boot-bridge.sh**: Termux:Boot compatibility script.
4. **ecosystem.config.js**: PM2 process management.

## Monitoring
Check health at: https://zenith.cosmic-claw.com/health
Real-time alerts via ntfy topic: `tcc-zenith-hive`
