"""Stage 4, part 2: all three primitives, used the way they were designed for an LLM.

    PROMPT   -> the USER picks "travel_advice" and fills in city + days.
                The host turns it into the message sent to the model.
    RESOURCE -> the HOST (this script) reads weather://cities and puts it in the
                system message, so the model knows which cities have data.
    TOOL     -> the MODEL decides to call get_weather while answering.

Three primitives, three different deciders: user, host, model.

Usage:
    python llm_client.py
    python llm_client.py Tokyo 5
"""
import asyncio, json, os, sys
from pathlib import Path

from mcp import Client, StdioServerParameters
from openai import AsyncOpenAI

SERVER = Path(__file__).with_name("weather_server.py")
MODEL = os.environ.get("OPENAI_MODEL", "gpt-5.4-mini")


def to_openai_tool(tool) -> dict:
    return {"type": "function", "function": {
        "name": tool.name, "description": tool.description, "parameters": tool.input_schema}}


async def ask(llm, mcp, tools, messages: list, max_rounds: int = 5) -> str:
    """The tool loop from Stage 3, taking a ready-made message list."""
    for _ in range(max_rounds):
        reply = (await llm.chat.completions.create(
            model=MODEL, messages=messages, tools=tools)).choices[0].message
        if not reply.tool_calls:
            return reply.content
        messages.append(reply.model_dump(include={"role", "content", "tool_calls"}, exclude_none=True))
        for call in reply.tool_calls:
            args = json.loads(call.function.arguments)
            result = await mcp.call_tool(call.function.name, args)
            text = "\n".join(c.text for c in result.content if hasattr(c, "text"))
            print(f"  [TOOL, model decided]  {call.function.name}({args}) -> {text.replace(chr(10), ' ')}")
            messages.append({"role": "tool", "tool_call_id": call.id, "content": text})
    return "(stopped: too many rounds)"


async def main():
    if not os.environ.get("OPENAI_API_KEY"):
        sys.exit("Set OPENAI_API_KEY first. See 'Set up your OpenAI key' in the main README.")
    city = sys.argv[1] if len(sys.argv) > 1 else "Tokyo"
    days = sys.argv[2] if len(sys.argv) > 2 else "3"
    llm = AsyncOpenAI()

    async with Client(StdioServerParameters(command=sys.executable, args=[str(SERVER)])) as mcp:
        tools = [to_openai_tool(t) for t in (await mcp.list_tools()).tools]

        # PROMPT: the user picked a template. Prompt arguments always travel as text.
        prompt = await mcp.get_prompt("travel_advice", {"city": city, "days": days})
        user_text = prompt.messages[0].content.text
        print(f"[PROMPT, user picked]   travel_advice(city={city}, days={days})")
        print(f"                        -> \"{user_text}\"")

        # RESOURCE: the host decides to attach some background data
        cities = (await mcp.read_resource("weather://cities")).contents[0].text
        system = ("You are a friendly travel helper. Weather data exists only for these "
                  f"cities: {', '.join(cities.splitlines())}. For other cities, say you have no data.")
        print(f"[RESOURCE, host added]  weather://cities -> {cities.splitlines()}")

        messages = [{"role": "system", "content": system},
                    {"role": "user", "content": user_text}]
        print("\nmodel:", await ask(llm, mcp, tools, messages))


if __name__ == "__main__":
    asyncio.run(main())
