import asyncio
import sys
from pathlib import Path

from mcp import Client, StdioServerParameters

SERVER = Path(__file__).with_name("my_server.py")


async def main():
    # Point the client at the server file. It launches it as a subprocess
    # and talks to it over stdin/stdout (the "stdio" transport).
    params = StdioServerParameters(command=sys.executable, args=[str(SERVER)])
    client = Client(params)

    async with client:
        # Discovery: ask the server what it can do
        tools = await client.list_tools()
        print("Available tools:")
        for tool in tools.tools:
            print(f"  - {tool.name}: {tool.description}")
            # The type hints on the server function became this JSON Schema
            print(f"    input schema: {tool.input_schema['properties']}")

        print("\n" + "=" * 50 + "\n")

        # Execution: call a tool by name with arguments
        result = await client.call_tool("get_weather", {"city": "New york"})
        print(f"Weather result: {result.content[0].text}")


if __name__ == "__main__":
    asyncio.run(main())
