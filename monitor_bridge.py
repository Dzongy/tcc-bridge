
import time
import requests
import os

NTFY_URL = "https://ntfy.sh/tcc-zenith-hive"
HEALTH_URL = "http://localhost:8080/health"
PUBLIC_HEALTH_URL = "https://zenith.cosmic-claw.com/health"

def alert(msg):
    try:
        requests.post(NTFY_URL, data=msg.encode('utf-8'), headers={
            "Title": "Bridge Alert",
            "Priority": "5",
            "Tags": "warning,robot"
        })
    except:
        pass

def check():
    # Check local
    try:
        resp = requests.get(HEALTH_URL, timeout=5)
        if resp.status_code != 200:
            alert("Local Bridge is DOWN (Status: " + str(resp.status_code) + ")")
    except Exception as e:
        alert("Local Bridge is UNREACHABLE: " + str(e))
    
    # Check public
    try:
        resp = requests.get(PUBLIC_HEALTH_URL, timeout=10)
        if resp.status_code != 200:
            alert("Public Bridge Tunnel is DOWN (Status: " + str(resp.status_code) + ")")
    except Exception as e:
        alert("Public Bridge Tunnel is UNREACHABLE (Tunnel issue)")

if __name__ == "__main__":
    while True:
        check()
        time.sleep(300) # Check every 5 minutes
