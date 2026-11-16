"""Stage 6: same idea, new transport. Run as a real network service.

stdio  -> client launches the server as a child process (local, one client)
HTTP   -> server runs on its own, many clients connect to a URL (remote, shared)

Only the last line differs from stage 1. The tools did not change.
"""
import sys
from mcp.server.mcpserver import MCPServer

mcp = MCPServer("weather-http")
VISITS = {"count": 0}  # shared by every client, proving it is one process


@mcp.tool()
def get_weather(city: str) -> dict:
    """Get the current weather for a city."""
    VISITS["count"] += 1
    data = {"new york": (72, "sunny"), "london": (59, "cloudy"), "tokyo": (68, "rainy")}
    temp, cond = data.get(city.lower(), (70, "unknown"))
    return {"city": city, "temp": temp, "condition": cond, "total_calls_on_server": VISITS["count"]}


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
    mcp.run(transport="streamable-http", host="127.0.0.1", port=port)
