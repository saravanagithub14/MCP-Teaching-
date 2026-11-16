"""Stage 4: MCP is not only tools. Three primitives.

  Tool     -> model-controlled. The LLM decides to call it.      (actions)
  Resource -> app-controlled.   The host attaches it as context. (data)
  Prompt   -> user-controlled.  The user picks a template.       (workflows)
"""
from mcp.server.mcpserver import MCPServer
from mcp.types import ToolAnnotations

mcp = MCPServer("weather-full")

WEATHER = {
    "new york": {"temp": 72, "condition": "sunny"},
    "london": {"temp": 59, "condition": "cloudy"},
    "tokyo": {"temp": 68, "condition": "rainy"},
}


# ---- Tool: an action the model can ask for ----
@mcp.tool(annotations=ToolAnnotations(read_only_hint=True))  # only reads, safe to run
def get_weather(city: str) -> dict:
    """Get the current weather for a city."""
    return {"city": city, **WEATHER.get(city.lower(), {"temp": 70, "condition": "unknown"})}


# ---- Resource: fixed URI, read-only data ----
@mcp.resource("weather://cities")
def list_cities() -> str:
    """Cities this server has data for."""
    return "\n".join(sorted(WEATHER))


# ---- Resource template: URI with a parameter ----
@mcp.resource("weather://city/{name}")
def city_report(name: str) -> str:
    """Plain text report for one city."""
    w = WEATHER.get(name.lower())
    if not w:
        return f"No data for {name}"
    return f"{name.title()}: {w['temp']}F and {w['condition']}"


# ---- Prompt: a reusable template the user picks ----
@mcp.prompt()
def travel_advice(city: str, days: int = 3) -> str:
    """Ask the model for packing advice, using this server's weather tool."""
    return (
        f"I'm visiting {city} for {days} days. Use the get_weather tool to check "
        f"the weather there, then tell me what to pack. Keep it under 80 words."
    )


if __name__ == "__main__":
    mcp.run(transport="stdio")
