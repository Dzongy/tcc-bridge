
#!/bin/bash
# Check if script is already running
if pidof -x "python3 bridge_v2.py" > /dev/null; then
    exit
fi
cd ~/tcc-bridge
python3 bridge_v2.py
