import asyncio, sys
from pathlib import Path
from mcp import Client, StdioServerParameters

SERVER = Path(__file__).with_name("weather_server.py")


async def main():
    async with Client(StdioServerParameters(command=sys.executable, args=[str(SERVER)])) as c:
        print("== TOOLS (model decides) ==")
        print([t.name for t in (await c.list_tools()).tools])

        print("\n== RESOURCES (app attaches) ==")
        for r in (await c.list_resources()).resources:
            print("-", r.uri)
        for t in (await c.list_resource_templates()).resource_templates:
            print("- template:", t.uri_template)
        print("read weather://cities ->", (await c.read_resource("weather://cities")).contents[0].text.replace("\n", ", "))
        print("read weather://city/tokyo ->", (await c.read_resource("weather://city/tokyo")).contents[0].text)

        print("\n== PROMPTS (user picks) ==")
        for p in (await c.list_prompts()).prompts:
            print("-", p.name, [a.name for a in (p.arguments or [])])
        got = await c.get_prompt("travel_advice", {"city": "London", "days": "2"})
        print("rendered ->", got.messages[0].content.text)


asyncio.run(main())
