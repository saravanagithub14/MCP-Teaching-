"""Stage 2: what MCP really is. JSON-RPC 2.0 messages over a pipe.

No MCP SDK on the client side. We spawn the stage 1 server and write
JSON lines to its stdin, then read its stdout. Every line printed with
-> is what we sent, every line with <- is what the server answered.
"""
import json
import subprocess
import sys
from pathlib import Path

SERVER = Path(__file__).with_name("my_server.py")

proc = subprocess.Popen(
    [sys.executable, str(SERVER)],
    stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, bufsize=1,
)


def send(msg: dict):
    print("->", json.dumps(msg))
    proc.stdin.write(json.dumps(msg) + "\n")
    proc.stdin.flush()


def recv() -> dict:
    line = proc.stdout.readline()
    print("<-", line.strip()[:400])
    return json.loads(line)


# 1. Handshake: client says who it is, server says what it supports
send({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
    "protocolVersion": "2025-06-18",
    "capabilities": {},
    "clientInfo": {"name": "raw-client", "version": "0.1"},
}})
init = recv()
send({"jsonrpc": "2.0", "method": "notifications/initialized"})  # no id = no reply

# 2. Discovery
send({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
recv()

# 3. Execution
send({"jsonrpc": "2.0", "id": 3, "method": "tools/call",
      "params": {"name": "get_weather", "arguments": {"city": "London"}}})
recv()

proc.stdin.close()
proc.wait(timeout=5)
