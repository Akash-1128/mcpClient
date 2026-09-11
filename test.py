import os
import httpx
from dotenv import load_dotenv

load_dotenv()

url = os.environ["MCP_URL"]
client_id = os.environ["MCP_CLIENT_ID"]
client_secret = os.environ["MCP_CLIENT_SECRET"]

initialize_request = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
        "protocolVersion": "2025-06-18",
        "capabilities": {},
        "clientInfo": {
            "name": "test-client",
            "version": "1.0.0"
        }
    }
}

headers = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
}

response = httpx.post(
    url,
    json=initialize_request,
    headers=headers,
    auth=httpx.BasicAuth(client_id, client_secret),
    timeout=30.0,
)

print("Status:", response.status_code)
print("Headers:", dict(response.headers))
print("Response:", response.text)