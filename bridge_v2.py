#!/usr/bin/env python3
"""
TCC Bridge v2.0 — The Permanent Bridge
Push-based architecture: Device pushes state TO Supabase AND ntfy
No server on phone required. Agents read from DB or ntfy anytime.

Author: ZENITH / TCC
Version: 2.0.0
"""

import os
import sys
import json
import time
import subprocess
import requests
from datetime import datetime
from typing import Dict, Any, Optional, List

# Configuration
SUPABASE_URL = "https://vbqbbziqleymxcyesmky.supabase.co"
SUPABASE_KEY = "sb_secret_lIbl-DBgdnrt_fejgJjKqg_qR62SVEm"
DEVICE_ID = "amos-arms"
NTFY_TOPIC = "zenith-escape"
HEARTBEAT_INTERVAL = 300  # 5 minutes

class TCCBridgeV2:
    """Push-based bridge — device reports to Supabase + ntfy, agents read from anywhere"""
    
    def __init__(self):
        self.supabase_url = SUPABASE_URL
        self.supabase_key = SUPABASE_KEY
        self.device_id = DEVICE_ID
        self.ntfy_topic = NTFY_TOPIC
        self.session = requests.Session()
        self.session.headers.update({
            "apikey": self.supabase_key,
            "Authorization": f"Bearer {self.supabase_key}",
            "Content-Type": "application/json"
        })
    
    def run_shell(self, cmd: str) -> str:
        """Execute shell command and return output"""
        try:
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True, timeout=30
            )
            return result.stdout.strip() or result.stderr.strip() or "null"
        except Exception as e:
            return f"error: {str(e)}"
    
    def get_installed_apps(self) -> List[str]:
        """Get list of installed packages"""
        output = self.run_shell("pm list packages")
        apps = []
        for line in output.split('\n'):
            if line.startswith('package:'):
                apps.append(line.replace('package:', ''))
        return apps[:100]  # Limit to first 100 for size
    
    def get_battery_info(self) -> dict:
        """Get battery level and status"""
        output = self.run_shell("dumpsys battery")
        info = {}
        for line in output.split('\n'):
            if 'level:' in line:
                try:
                    info['level'] = int(line.split(':')[1].strip())
                except:
                    pass
            if 'status:' in line:
                info['status'] = line.split(':')[1].strip()
            if 'plugged:' in line:
                info['plugged'] = line.split(':')[1].strip()
        return info
    
    def get_storage_info(self) -> dict:
        """Get storage usage"""
        output = self.run_shell("df -h /data")
        lines = output.split('\n')
        if len(lines) > 1:
            parts = lines[1].split()
            if len(parts) >= 6:
                return {
                    'size': parts[1],
                    'used': parts[2],
                    'available': parts[3],
                    'use_percent': parts[4]
                }
        return {}
    
    def get_network_info(self) -> str:
        """Get network connection type"""
        wifi = self.run_shell("dumpsys wifi | grep 'Wi-Fi is' | head -1")
        if 'enabled' in wifi.lower():
            ssid = self.run_shell("dumpsys wifi | grep 'SSID:' | head -1")
            return f"wifi:{ssid.split(':')[1].strip() if ':' in ssid else 'unknown'}"
        
        mobile = self.run_shell("dumpsys telephony.registry | grep 'mDataConnectionState' | head -1")
        if '2' in mobile:
            return "mobile:data"
        
        return "offline"
    
    def get_device_info(self) -> dict:
        """Get device metadata"""
        return {
            'termux_version': self.run_shell("termux-info 2>/dev/null | head -1 || echo 'unknown'"),
            'android_version': self.run_shell("getprop ro.build.version.release"),
            'hostname': self.run_shell("hostname"),
            'model': self.run_shell("getprop ro.product.model"),
            'timestamp': datetime.utcnow().isoformat()
        }
    
    def push_to_supabase(self, payload: dict) -> bool:
        """Push device state to Supabase"""
        try:
            response = self.session.post(
                f"{self.supabase_url}/rest/v1/device_state",
                json=payload
            )
            
            if response.status_code in [200, 201]:
                print("[OK] Supabase updated")
                return True
            else:
                print(f"[FAIL] Supabase: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"[ERROR] Supabase: {str(e)}")
            return False
    
    def push_to_ntfy(self, state: dict) -> bool:
        """Push device state summary to ntfy"""
        try:
            battery = state.get('battery', {})
            network = state.get('network', 'unknown')
            storage = state.get('storage', {})
            
            message = f"📁 {self.device_id} | 😇 <battery.get('level', '?')% | 😀 {Network} | 🍎 {storage.get('use_percent', '?')}"
            
            response = requests.post(
                f"https://ntfy.sh/{self.ntfy_topic}",
                data=message,
                headers={
                    "Title": f"TCC Bridge v2 — {datetime.now().strftime('%H:%M')}",
                    "Priority": "default",
                    "Tags": "bridge,heartbeat,amos-arms"
                },
                timeout=10
            )
            
            if response.status_code == 200:
                print("[OK] ntfy notified")
                return True
            else:
                print(f"[FAIL] ntfy: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"[ERROR] ntfy: {str(e)}")
            return False
    
    def push_state(self) -> bool:
        """Push device state to both Supabase and ntfy"""
        try:
            state = {
                'device_id': self.device_id,
                'apps_json': self.get_installed_apps(),
                'battery': self.get_battery_info(),
                'network': self.get_network_info(),
                'storage': self.get_storage_info(),
                'raw_output': json.dumps(self.get_device_info()),
                'termux_version': self.get_device_info().get('termux_version'),
                'android_version': self.get_device_info().get('android_version'),
                'hostname': self.get_device_info().get('hostname')
            }
            
            supabase_ok = self.push_to_supabase(state)
            ntfy_ok = self.push_to_ntfy(state)
            
            if supabase_ok and ntfy_ok:
                print(f"[OK] State pushed at {datetime.now().isoformat()}")
                return True
            else:
                print(f"[WARN] Partial: Supabase={supabase_ok}, ntfy={ntfy_ok}")
                return supabase_ok or ntfy_ok
                
        except Exception as e:
            print(f"[ERROR] Push failed: {str(e)}")
            return False
    
    def run_heartbeat(self):
        """Run continuous heartbeat loop"""
        print("=" * 60)
        print("TCC Bridge v2.0 — Push-Based Architecture")
        print(f"Device: {self.device_id}")
        print(f"Supabase: {self.supabase_url}")
        print(f"ntfy: https://ntfy.sh/{self.ntfy_topic}")
        print(f"Interval: {HEARTBEAT_INTERVAL}s")
        print("=" * 60)
        
        while True:
            self.push_state()
            time.sleep(HEARTBEAT_INTERVAL)


def main():
    """Entry point"""
    bridge = TCCBridgeV2()
    
    if len(sys.argv) > 1:
        if sys.argv[1] == '--once':
            success = bridge.push_state()
            sys.exit(0 if success else 1)
        elif sys.argv[1] == '--apps':
            apps = bridge.get_installed_apps()
            print(json.dumps(apps, indent=2))
        elif sys.argv[1] == '--status':
            print(json.dumps({
                'battery': bridge.get_battery_info(),
                'network': bridge.get_network_info(),
                'storage': bridge.get_storage_info(),
                'device': bridge.get_device_info()
            }, indent=2))
        elif sys.argv[1] == '--ntfy-only':
            state = {
                'device_id': bridge.device_id,
                'battery': bridge.get_battery_info(),
                'network': bridge.get_network_info(),
                'storage': bridge.get_storage_info()
            }
            bridge.push_to_ntfy(state)
    else:
        bridge.run_heartbeat()

if __name__ == "__main__":
    main()
