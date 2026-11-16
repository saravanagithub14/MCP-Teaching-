"""Stage 3: tools get richer. Types become contracts.

New vs stage 1:
  - Literal / enum args  -> every client sees the allowed values
  - Pydantic return type -> structured output with an output schema
  - ToolError            -> isError=true with YOUR message, so the caller can fix the call
  - Any other exception  -> isError=true but the message is hidden (safe by default)
"""
from typing import Literal

from pydantic import BaseModel, Field
from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

mcp = MCPServer("weather-typed")

WEATHER = {
    "new york": (72, "sunny"),
    "london": (59, "cloudy"),
    "tokyo": (68, "rainy"),
}


class Weather(BaseModel):
    city: str
    temp_f: float = Field(description="Temperature in Fahrenheit")
    condition: str


@mcp.tool()
def get_weather(city: str) -> Weather:
    """Get the current weather for a city (mock data)."""
    temp, cond = WEATHER.get(city.lower(), (70, "unknown"))
    return Weather(city=city, temp_f=temp, condition=cond)


@mcp.tool()
def convert_temperature(
    temp: float,
    from_unit: Literal["C", "F"],
    to_unit: Literal["C", "F"],
) -> dict:
    """Convert a temperature between Celsius and Fahrenheit."""
    if from_unit == to_unit:
        return {"value": temp, "unit": to_unit}
    if from_unit == "C":
        return {"value": round(temp * 9 / 5 + 32, 1), "unit": "F"}
    return {"value": round((temp - 32) * 5 / 9, 1), "unit": "C"}


@mcp.tool()
def forecast(city: str, days: int = 3) -> list[Weather]:
    """Mock multi-day forecast. days must be between 1 and 7."""
    if not 1 <= days <= 7:
        # An error you anticipated: say what went wrong so the caller can retry
        raise ToolError("days must be between 1 and 7")
    base, cond = WEATHER.get(city.lower(), (70, "unknown"))
    return [Weather(city=city, temp_f=base + i, condition=cond) for i in range(days)]


@mcp.tool()
def buggy() -> str:
    """Deliberately crashes, to show that unexpected errors are masked."""
    return 1 / 0


if __name__ == "__main__":
    mcp.run(transport="stdio")
