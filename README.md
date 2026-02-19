# Zenith Bridge v2.0 (Push-Based)

The Permanent Bridge for TCC Sovereignty.

## Installation
Run this command in Termux:
\`bash
curl -sL https://raw.githubusercontent.com/Dzongy/tcc-bridge/main/setup.sh | bash
\`

## Architecture
- `bridge_v2.py`: Main state collector and pusher.
- `push_state.sh`: Cron wrapper with PID locking.
- `setup.sh`: Automated installer.

## Features
- Pushes to Supabase every 5 minutes.
- Collects: Apps, Battery, Network, Storage.
- $0 cost, zero maintenance.
