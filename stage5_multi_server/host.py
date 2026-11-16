"""A tiny, general MCP *host*: owns several clients, merges their tools, routes calls.

The host knows nothing about weather or notes. It reads a list of servers from
servers.json, connects to each one, and only ever speaks MCP. Add a server to
the config and the host picks it up with no code changes.

Config format (the same shape most MCP host apps use):
    {"servers": {"<name>": {"command": "python", "args": ["server.py"]}}}
"""
import asyncio, json, sys
from contextlib import AsyncExitStack
from pathlib import Path
from mcp import Client, StdioServerParameters

HERE = Path(__file__).parent


def load_config(path: Path) -> dict[str, StdioServerParameters]:
    """Turn the JSON config into launch settings, one per server."""
    servers = json.loads(path.read_text())["servers"]
    params = {}
    for name, cfg in servers.items():
        # "python" means "the Python running this host", so it works in any venv
        command = sys.executable if cfg["command"] == "python" else cfg["command"]
        params[name] = StdioServerParameters(
            command=command, args=cfg.get("args", []), env=cfg.get("env"), cwd=str(path.parent))
    return params


class Host:
    def __init__(self, config: Path = HERE / "servers.json"):
        self.config = config
        self.stack = AsyncExitStack()
        self.clients: dict[str, Client] = {}
        self.routes: dict[str, tuple[str, str]] = {}  # public name -> (server, tool)
        self.catalog: list[dict] = []                 # every tool from every server

    async def start(self):
        for name, params in load_config(self.config).items():
            self.clients[name] = await self.stack.enter_async_context(Client(params))
            for t in (await self.clients[name].list_tools()).tools:
                public = f"{name}__{t.name}"  # namespace avoids name clashes
                self.routes[public] = (name, t.name)
                read_only = bool(t.annotations and t.annotations.read_only_hint)
                self.catalog.append({"name": public, "description": t.description or "",
                                     "input_schema": t.input_schema, "read_only": read_only})

    async def call(self, public_name: str, args: dict) -> str:
        if public_name not in self.routes:
            return f"ERROR: no tool named {public_name}"
        server, tool = self.routes[public_name]
        r = await self.clients[server].call_tool(tool, args)
        # A result can hold several content items (a list returns one per item)
        text = "\n".join(c.text for c in r.content if getattr(c, "text", None) is not None)
        return f"ERROR: {text}" if r.is_error else text

    async def close(self):
        await self.stack.aclose()


def one_line(text: str) -> str:
    """Squash a result onto one line for printing (JSON stays valid JSON)."""
    try:
        return json.dumps(json.loads(text))
    except ValueError:
        return text.replace("\n", " | ")


async def main():
    host = Host()
    await host.start()
    try:
        print(f"Connected to {len(host.clients)} servers from {host.config.name}\n")
        print("Merged tool catalog:")
        for t in host.catalog:
            print(f"  {t['name']:<22} {t['description']}")

        print("\nRouting calls to different servers:")
        for name, args in [("weather__get_weather", {"city": "London"}),
                           ("notes__add_note", {"text": "pack an umbrella"}),
                           ("notes__add_note", {"text": "charge the phone"}),
                           ("notes__list_notes", {})]:
            out = one_line(await host.call(name, args))
            print(f"  {name:<22} -> {out}")
    finally:
        await host.close()


if __name__ == "__main__":
    asyncio.run(main())
