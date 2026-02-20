#!/bin/bash
# Bridge v2 Push State Cron Job

# Navigate to script directory
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

# Run the bridge script
python3 bridge_v2.py >> bridge.log 2>&1
