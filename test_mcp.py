import os
import httpx
from dotenv import load_dotenv

load_dotenv()

url = os.environ["MCP_URL"]
client_id = os.environ["MCP_CLIENT_ID"]
client_secret = os.environ["MCP_CLIENT_SECRET"]

print("URL:", url)
print("CLIENT ID:", client_id)
print("SECRET LENGTH:", len(client_secret))

payload = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
        "protocolVersion": "2025-06-18",
        "capabilities": {},
        "clientInfo": {
            "name": "render-test",
            "version": "1.0"
        }
    }
}

headers = {
    "Accept": "application/json, text/event-stream",
    "Content-Type": "application/json",
}

print("Sending request...")

try:
    response = httpx.post(
        url,
        auth=httpx.BasicAuth(client_id, client_secret),
        headers=headers,
        json=payload,
        timeout=30,
    )

    print("STATUS:", response.status_code)
    print("HEADERS:", dict(response.headers))
    print("BODY:", response.text[:2000])

except Exception as e:
    print("ERROR:", repr(e))