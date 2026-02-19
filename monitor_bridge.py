
import time, requests, json, os

NTFY_URL = "https://ntfy.sh/tcc-zenith-hive"
HEALTH_URL = "http://localhost:8080/health"

def alert(msg, priority=5):
    try:
        requests.post(NTFY_URL, data=msg.encode('utf-8'), headers={
            "Title": "Bridge Status",
            "Priority": str(priority),
            "Tags": "robot,warning" if priority > 3 else "robot,check"
        })
    except: pass

last_status = True

while True:
    try:
        resp = requests.get(HEALTH_URL, timeout=5)
        if resp.status_code == 200:
            if not last_status:
                alert("Bridge RECOVERED", priority=3)
                last_status = True
        else:
            if last_status:
                alert(f"Bridge unhealthy (Status: {resp.status_code})")
                last_status = False
    except Exception as e:
        if last_status:
            alert(f"Bridge UNREACHABLE: {str(e)}")
            last_status = False
    
    time.sleep(300)
