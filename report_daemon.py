import time
import re
import os
import requests

GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN')
REPO = "Dzongy/tcc-bridge"
FILE_PATH = "bridge_url.json"

def get_tunnel_url():
    try:
        with open("tunnel.log", "r") as f:
            content = f.read()
            match = re.search(r'https://[a-zA-Z0-9-]+.trycloudflare.com', content)
            if match:
                return match.group(0)
    except:
        pass
    return None

def update_github(url):
    if not GITHUB_TOKEN:
        print("[WARN] No GITHUB_TOKEN found. Cannot report URL.")
        return
    
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    # Get SHA
    sha = None
    r = requests.get(f"https://api.github.com/repos/{REPO}/contents/{FILE_PATH}", headers=headers)
    if r.status_code == 200:
        sha = r.json().get('sha')
    
    import base64
    import json
    
    content_str = json.dumps({"url": url, "updated": time.time()})
    content_b64 = base64.b64encode(content_str.encode()).decode()

    data = {
        "message": "Update bridge URL [skip ci]",
        "content": content_b64,
        "sha": sha
    }
    
    r = requests.put(f"https://api.github.com/repos/{REPO}/contents/{FILE_PATH}", headers=headers, json=data)
    if r.status_code in [200, 201]:
        print(f"[SUCCESS] Updated GitHub with new URL: {url}")
    else:
        print(f"[ERROR] Failed to update GitHub: {r.status_code} {r.text}")

print("Daemon started...")
last_url = None
while True:
    url = get_tunnel_url()
    if url and url != last_url:
        print(f"New Tunnel URL: {url}")
        update_github(url)
        last_url = url
    time.sleep(10)
