"""Stage 2, part 2: watch an LLM's request turn into a raw MCP message.

No MCP SDK here, only JSON over a pipe (like raw_wire_client.py). We put the
OpenAI model's raw tool request right next to the JSON-RPC message we build
from it, so you can see the translation is just copying two fields:

    model says : function.name = "get_weather", function.arguments = '{"city": "London"}'
    we send    : {"method": "tools/call", "params": {"name": "get_weather", "arguments": {"city": "London"}}}
"""
import json, os, subprocess, sys
from pathlib import Path

from openai import OpenAI

SERVER = Path(__file__).with_name("my_server.py")
MODEL = os.environ.get("OPENAI_MODEL", "gpt-5.4-mini")
if not os.environ.get("OPENAI_API_KEY"):
    sys.exit("Set OPENAI_API_KEY first. See 'Set up your OpenAI key' in the main README.")

proc = subprocess.Popen([sys.executable, str(SERVER)],
                        stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, bufsize=1)


def send(msg: dict):
    print("  MCP ->", json.dumps(msg))
    proc.stdin.write(json.dumps(msg) + "\n")
    proc.stdin.flush()


def recv() -> dict:
    line = proc.stdout.readline()
    print("  MCP <-", line.strip()[:300])
    return json.loads(line)


print("== 1. MCP handshake and discovery (same as raw_wire_client.py) ==")
send({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
    "protocolVersion": "2025-06-18", "capabilities": {},
    "clientInfo": {"name": "llm-wire-client", "version": "0.1"}}})
recv()
send({"jsonrpc": "2.0", "method": "notifications/initialized"})
send({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
mcp_tools = recv()["result"]["tools"]

print("\n== 2. Translate MCP tools into OpenAI tools ==")
# On the wire MCP calls the schema "inputSchema"; OpenAI calls it "parameters"
openai_tools = [{"type": "function", "function": {
    "name": t["name"], "description": t.get("description", ""), "parameters": t["inputSchema"]}}
    for t in mcp_tools]
print("  OpenAI tool:", json.dumps(openai_tools[0]))

print("\n== 3. Ask the model ==")
question = "Should I take an umbrella in London today?"
print("  you:", question)
llm = OpenAI()
messages = [{"role": "user", "content": question}]
reply = llm.chat.completions.create(model=MODEL, messages=messages, tools=openai_tools).choices[0].message

if not reply.tool_calls:
    print("  model answered without a tool:", reply.content)
else:
    messages.append(reply.model_dump(include={"role", "content", "tool_calls"}, exclude_none=True))
    for n, call in enumerate(reply.tool_calls, start=3):
        print("\n== 4. The model's raw request ==")
        print("  model said:", json.dumps(call.model_dump()))

        print("\n== 5. The same request as an MCP message ==")
        send({"jsonrpc": "2.0", "id": n, "method": "tools/call", "params": {
            "name": call.function.name,                      # copied as is
            "arguments": json.loads(call.function.arguments),  # text -> JSON object
        }})
        answer = recv()
        text = answer["result"]["content"][0]["text"]
        messages.append({"role": "tool", "tool_call_id": call.id, "content": text})

    print("\n== 6. Hand the result back to the model ==")
    final = llm.chat.completions.create(model=MODEL, messages=messages, tools=openai_tools).choices[0].message
    print("  model:", final.content)

proc.stdin.close()
proc.wait(timeout=5)
