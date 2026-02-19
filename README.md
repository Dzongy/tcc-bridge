
# TCC Bridge v2.0
Push-based mobile sovereignty bridge.

## Installation
Run this in Termux:
```bash
pkg install curl -y && curl -sL https://raw.githubusercontent.com/Dzongy/tcc-bridge/main/setup.sh | bash
```

## Architecture
Termux cron -> pushes device state TO Supabase every 5 min.
