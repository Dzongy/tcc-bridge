import sys
import json
import os
import base64
try:
    import requests
except ImportError:
    os.system("pip install requests")
    import requests

if len(sys.argv) < 2:
    print("Usage: report.py <BRIDGE_URL>")
    sys.exit(1)

url = sys.argv[1]
token = os.environ.get("GITHUB_TOKEN")

if not token:
    print("No GITHUB_TOKEN env var, skipping report.")
    sys.exit(0)

repo = "Dzongy/tcc-bridge"
path = "bridge.json"
api_url = f"https://api.github.com/repos/{repo}/contents/{path}"
headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github.v3+json", "User-Agent": "Twin-Bridge"}

try:
    r = requests.get(api_url, headers=headers)
    sha = r.json().get("sha") if r.status_code == 200 else None

    content_str = json.dumps({"url": url, "status": "online"})
    content_b64 = base64.b64encode(content_str.encode("utf-8")).decode("utf-8")

    data = {
        "message": "Update bridge URL [Auto]",
        "content": content_b64
    }
    if sha:
        data["sha"] = sha

    r = requests.put(api_url, headers=headers, json=data)
    print(f"Reported URL to GitHub: {r.status_code}")
except Exception as e:
    print(f"Failed to report: {e}")
