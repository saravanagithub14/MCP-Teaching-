"""Stage 3, part 2: an OpenAI model uses the typed tools, and fixes its own mistakes.

New vs stage 1: a LOOP. Stage 1 allowed one round of tool calls. Here the model
can call tools again and again until it has what it needs. That matters when:
  - it needs several tools, one after another
  - a tool says "you got that wrong" (ToolError) and the model tries again

Watch for the forecast question. Our tool only allows 1 to 7 days. The model
asks for 10, gets the ToolError message, and retries with a valid value.
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


async def ask(llm, mcp, tools, question: str, max_rounds: int = 5) -> str:
    """Send a question, run whatever tools the model asks for, repeat until it answers."""
    messages = [{"role": "user", "content": question}]
    for _ in range(max_rounds):
        reply = (await llm.chat.completions.create(
            model=MODEL, messages=messages, tools=tools)).choices[0].message
        if not reply.tool_calls:          # no tool requests means: this is the answer
            return reply.content
        messages.append(reply.model_dump(include={"role", "content", "tool_calls"}, exclude_none=True))
        for call in reply.tool_calls:
            args = json.loads(call.function.arguments)
            result = await mcp.call_tool(call.function.name, args)
            text = "\n".join(c.text for c in result.content if hasattr(c, "text"))
            mark = "ERROR" if result.is_error else "ok"
            print(f"    {call.function.name}({args}) -> [{mark}] {text.replace(chr(10), ' ')[:90]}")
            # Errors go back to the model too. That is how it learns to fix the call.
            messages.append({"role": "tool", "tool_call_id": call.id, "content": text})
    return "(stopped: too many rounds)"


async def main():
    if not os.environ.get("OPENAI_API_KEY"):
        sys.exit("Set OPENAI_API_KEY first. See 'Set up your OpenAI key' in the main README.")
    llm = AsyncOpenAI()
    async with Client(StdioServerParameters(command=sys.executable, args=[str(SERVER)])) as mcp:
        listed = (await mcp.list_tools()).tools
        # buggy() exists only to show masked errors in client.py; don't offer it to the model
        tools = [to_openai_tool(t) for t in listed if t.name != "buggy"]
        convert = next(t for t in listed if t.name == "convert_temperature")
        enum = convert.input_schema["properties"]["from_unit"]
        print("The model sees from_unit as:", json.dumps(enum), "\n")

        for question in [
            "What is 100 degrees Celsius in Fahrenheit?",
            "Give me a 10-day forecast for London.",
        ]:
            print("you  :", question)
            print("model:", await ask(llm, mcp, tools, question), "\n")


if __name__ == "__main__":
    asyncio.run(main())
