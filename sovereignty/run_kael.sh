#!/bin/bash
# run_kael.sh â TCC Sovereignty Wrapper
# Prevents SIGINT from killing python during urllib3 import
trap "" INT
cd /data/data/com.termux/files/home/tcc-bridge/sovereignty
exec python3 -c "
import signal
signal.signal(signal.SIGINT, signal.SIG_IGN)
import runpy
runpy.run_path('agent_core.py', run_name='__main__')
"
