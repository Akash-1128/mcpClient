"""Exercise the A2A agent the same way Agent Fabric will: fetch the card,
then POST a message/send JSON-RPC call.

    python test_client.py "Summarize my spending for July 2026"

Point it at a deployment with AGENT_URL:

    AGENT_URL=https://expenseagent.onrender.com python test_client.py "..."
"""

import asyncio
import json
import os
import sys
import uuid

import httpx

BASE = os.environ.get("AGENT_URL", "http://localhost:9000").rstrip("/")


def print_parts(parts):
    for part in parts:
        if part.get("kind") == "text":
            print(f"\n{part['text']}")


async def main() -> None:
    query = " ".join(sys.argv[1:]) or "What expense categories exist?"

    async with httpx.AsyncClient(timeout=300) as http:
        card = (await http.get(f"{BASE}/.well-known/agent-card.json")).json()
        print("=== AGENT CARD ===")
        print(f"{card['name']} v{card['version']} -> {card['url']}")
        for skill in card["skills"]:
            print(f"  - {skill['id']}: {skill['name']}")

        payload = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": "message/send",
            "params": {
                "message": {
                    "kind": "message",
                    "role": "user",
                    "messageId": str(uuid.uuid4()),
                    "parts": [{"kind": "text", "text": query}],
                }
            },
        }
        print(f"\n=== message/send ===\n{query}\n")
        resp = await http.post(f"{BASE}/", json=payload)
        body = resp.json()

        if "error" in body:
            print(json.dumps(body["error"], indent=2))
            return

        result = body["result"]
        status = result.get("status", {})
        print(f"state: {status.get('state')}")

        # A failed task carries its reason in status.message; a completed one
        # puts the answer in artifacts. Print whichever is present.
        if status.get("message"):
            print_parts(status["message"].get("parts", []))

        for artifact in result.get("artifacts") or []:
            print_parts(artifact.get("parts", []))


if __name__ == "__main__":
    asyncio.run(main())
