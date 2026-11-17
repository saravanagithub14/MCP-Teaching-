"""Stage 1, part 2: let an OpenAI model use your MCP tool.

    you --question--> [this script] --question + tool list--> OpenAI model
                          |           <-- "please call get_weather(city=Tokyo)"
                          |--tools/call--> my_server.py   (this hop is MCP)
                          |           <-- {"temp": 68, ...}
                          |--tool result--> OpenAI model
                                      <-- "It's 68F and rainy in Tokyo."

The model never runs anything itself. It only *asks*. This script does the
asking-and-answering in between. That middle program is called the host.

Usage:
    python llm_chat.py
    python llm_chat.py "Is it sunny in New York?"
"""
import asyncio, json, os, sys
from pathlib import Path

from mcp import Client, StdioServerParameters
from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv(Path(__file__).resolve().parent.parent / ".env")  # reads OPENAI_API_KEY etc. from the repo-root .env

SERVER = Path(__file__).with_name("my_server.py")
MODEL = os.environ.get("OPENAI_MODEL", "gpt-5.4-mini")


def to_openai_tool(tool) -> dict:
    """MCP and OpenAI describe a tool with the same three facts, in different wrappers."""
    return {
        "type": "function",
        "function": {
            "name": tool.name,                  # what to call
            "description": tool.description,    # when to call it (the model reads this!)
            "parameters": tool.input_schema,    # what inputs it needs (from your type hints)
        },
    }


async def main():
    if not os.environ.get("OPENAI_API_KEY"):
        sys.exit("No OPENAI_API_KEY found. Add it to the .env file at the repo root. See 'Set up your OpenAI key' in the main README.")
    question = " ".join(sys.argv[1:]) or "What's the weather like in Tokyo right now?"
    llm = AsyncOpenAI()  # reads OPENAI_API_KEY (and OPENAI_BASE_URL, if you set one)

    async with Client(StdioServerParameters(command=sys.executable, args=[str(SERVER)])) as mcp:
        # 1. Discover the tools over MCP, then translate them into OpenAI's format
        tools = [to_openai_tool(t) for t in (await mcp.list_tools()).tools]
        print("tools given to the model:", [t["function"]["name"] for t in tools])
        print("\nyou  :", question)

        # 2. Send the question AND the tool list. The model decides if it needs a tool.
        messages = [{"role": "user", "content": question}]
        reply = (await llm.chat.completions.create(
            model=MODEL, messages=messages, tools=tools)).choices[0].message

        # 3. If the model asked for a tool, run it over MCP and hand back the result
        if reply.tool_calls:
            messages.append(reply.model_dump(include={"role", "content", "tool_calls"}, exclude_none=True))  # remember what it asked
            for call in reply.tool_calls:
                args = json.loads(call.function.arguments)  # the model sends args as JSON text
                print(f"  model asks for {call.function.name}({args})")
                result = await mcp.call_tool(call.function.name, args)
                text = result.content[0].text
                print(f"  MCP server replied {text.replace(chr(10), ' ')}")
                messages.append({"role": "tool", "tool_call_id": call.id, "content": text})

            # 4. Ask again. Now the model has the data, so it writes the answer.
            reply = (await llm.chat.completions.create(
                model=MODEL, messages=messages, tools=tools)).choices[0].message
        else:
            print("  (the model answered without using a tool)")

        print("model:", reply.content or "(it wanted another tool; Stage 3 adds a loop for that)")


if __name__ == "__main__":
    asyncio.run(main())
