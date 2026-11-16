"""Stage 6, part 2: an OpenAI model using a remote MCP server, reached by URL.

The model code is the same as in earlier stages. Only the line that connects
changed: Client(URL) instead of Client(StdioServerParameters(...)).

The model doesn't know or care whether the tool lives in a child process or on
another computer. The transport is the host's business, not the model's.
"""
import asyncio, json, os, socket, subprocess, sys, time
from pathlib import Path

from mcp import Client
from openai import AsyncOpenAI

PORT = 8766
URL = f"http://127.0.0.1:{PORT}/mcp"
MODEL = os.environ.get("OPENAI_MODEL", "gpt-5.4-mini")


def wait_for_port(port, timeout=15):
    end = time.time() + timeout
    while time.time() < end:
        with socket.socket() as s:
            if s.connect_ex(("127.0.0.1", port)) == 0:
                return
        time.sleep(0.2)
    raise RuntimeError("server did not start")


def to_openai_tool(tool) -> dict:
    return {"type": "function", "function": {
        "name": tool.name, "description": tool.description, "parameters": tool.input_schema}}


async def ask(llm, mcp, tools, question: str, max_rounds: int = 5) -> str:
    messages = [{"role": "user", "content": question}]
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
            print(f"  {call.function.name}({args}) over HTTP -> {text.replace(chr(10), ' ')}")
            messages.append({"role": "tool", "tool_call_id": call.id, "content": text})
    return "(stopped: too many rounds)"


async def main():
    if not os.environ.get("OPENAI_API_KEY"):
        sys.exit("Set OPENAI_API_KEY first. See 'Set up your OpenAI key' in the main README.")
    server = subprocess.Popen(
        [sys.executable, str(Path(__file__).with_name("http_server.py")), str(PORT)],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        wait_for_port(PORT)
        print(f"MCP server is up at {URL}\n")
        llm = AsyncOpenAI()
        async with Client(URL) as mcp:  # <- the only line that differs from stdio
            tools = [to_openai_tool(t) for t in (await mcp.list_tools()).tools]
            question = "What's the weather in Tokyo and in London?"
            print("you  :", question)
            print("model:", await ask(llm, mcp, tools, question))
    finally:
        server.terminate()
        server.wait(timeout=5)


if __name__ == "__main__":
    asyncio.run(main())
