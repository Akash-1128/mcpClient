import os
import asyncio
import httpx

from dotenv import load_dotenv
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

load_dotenv()

MCP_URL = os.environ["MCP_URL"]
CLIENT_ID = os.environ["MCP_CLIENT_ID"]
CLIENT_SECRET = os.environ["MCP_CLIENT_SECRET"]


async def main():
    print("URL:", MCP_URL)
    print("CLIENT ID:", CLIENT_ID)
    print("SECRET LENGTH:", len(CLIENT_SECRET))

    async with httpx.AsyncClient(
        auth=httpx.BasicAuth(CLIENT_ID, CLIENT_SECRET)
    ) as http_client:

        async with streamable_http_client(
            MCP_URL,
            http_client=http_client,
        ) as (read, write, _):

            async with ClientSession(read, write) as session:
                result = await session.initialize()

                print("INITIALIZED:", result.serverInfo)

                tools = await session.list_tools()

                print("TOOLS:")
                for tool in tools.tools:
                    print("-", tool.name)


if __name__ == "__main__":
    asyncio.run(main())