"""Stage 5, part 2: one OpenAI model, many MCP servers.

The host (host.py) connects to every server in servers.json and merges their
tools into one catalog. The model gets that whole catalog and can mix tools
from different servers in a single answer. It has no idea there are two
servers. The host routes each call to the right one.

    model --"weather__get_weather"--> host --> weather server
          --"notes__add_note"------>  host --> notes server

Usage:
    python chat.py
    python chat.py "Compare London and Tokyo, then save the warmer city as a note"
"""
import asyncio, json, os, sys
from pathlib import Path

from dotenv import load_dotenv
from openai import AsyncOpenAI
from host import Host, one_line

load_dotenv(Path(__file__).resolve().parent.parent / ".env")  # reads OPENAI_API_KEY etc. from the repo-root .env

MODEL = os.environ.get("OPENAI_MODEL", "gpt-5.4-mini")


def to_openai_tool(entry: dict) -> dict:
    """Same translation as before, but from the host's merged catalog."""
    return {"type": "function", "function": {
        "name": entry["name"], "description": entry["description"], "parameters": entry["input_schema"]}}


async def ask(llm, host: Host, question: str, max_rounds: int = 6) -> str:
    tools = [to_openai_tool(t) for t in host.catalog]
    messages = [{"role": "user", "content": question}]
    for _ in range(max_rounds):
        reply = (await llm.chat.completions.create(
            model=MODEL, messages=messages, tools=tools)).choices[0].message
        if not reply.tool_calls:
            return reply.content
        messages.append(reply.model_dump(include={"role", "content", "tool_calls"}, exclude_none=True))
        for call in reply.tool_calls:
            args = json.loads(call.function.arguments)
            server = host.routes[call.function.name][0] if call.function.name in host.routes else "?"
            text = await host.call(call.function.name, args)  # host routes it over MCP
            print(f"  {call.function.name}({args})  --routed to '{server}' server--> {one_line(text)[:70]}")
            messages.append({"role": "tool", "tool_call_id": call.id, "content": text})
    return "(stopped: too many rounds)"


async def main():
    if not os.environ.get("OPENAI_API_KEY"):
        sys.exit("No OPENAI_API_KEY found. Add it to the .env file at the repo root. See 'Set up your OpenAI key' in the main README.")
    question = " ".join(sys.argv[1:]) or (
        "What's the weather in London and Tokyo? Save a note comparing them, then show me all my notes.")
    llm = AsyncOpenAI()
    host = Host()
    await host.start()
    try:
        print("tools the model can use:", [t["name"] for t in host.catalog])
        print("\nyou  :", question)
        print("model:", await ask(llm, host, question))
    finally:
        await host.close()


if __name__ == "__main__":
    asyncio.run(main())
