import asyncio, json, sys
from pathlib import Path
from mcp import Client, StdioServerParameters

SERVER = Path(__file__).with_name("weather_server.py")


async def main():
    async with Client(StdioServerParameters(command=sys.executable, args=[str(SERVER)])) as c:
        print("== tools and their contracts ==")
        for t in (await c.list_tools()).tools:
            print(f"- {t.name}")
            print("   input :", json.dumps(t.input_schema.get("properties")))
            print("   output:", "yes (structured)" if t.output_schema else "no")

        print("\n== structured output ==")
        r = await c.call_tool("get_weather", {"city": "Tokyo"})
        print(r.structured_content)

        print("\n== enum arguments ==")
        r = await c.call_tool("convert_temperature", {"temp": 100, "from_unit": "C", "to_unit": "F"})
        print(r.content[0].text.replace("\n", " "))

        print("\n== bad argument (not in enum) ==")
        r = await c.call_tool("convert_temperature", {"temp": 1, "from_unit": "K", "to_unit": "F"})
        print("isError:", r.is_error, "|", r.content[0].text[:120].replace("\n", " "))

        print("\n== error raised inside the tool ==")
        r = await c.call_tool("forecast", {"city": "London", "days": 30})
        print("isError:", r.is_error, "|", r.content[0].text[:120])

        print("\n== unexpected crash (details hidden from the caller) ==")
        r = await c.call_tool("buggy", {})
        print("isError:", r.is_error, "|", r.content[0].text[:120])


asyncio.run(main())
