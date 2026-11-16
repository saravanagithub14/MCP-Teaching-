from mcp.server.mcpserver import MCPServer

# Initialize the server
mcp = MCPServer("my-first-server")


# Define a tool
@mcp.tool()
def get_weather(city: str) -> dict:
    """Get the current weather for a city."""
    # Mock weather data
    weather_data = {
        "new york": {"temp": 72, "condition": "sunny"},
        "london": {"temp": 59, "condition": "cloudy"},
        "tokyo": {"temp": 68, "condition": "rainy"},
    }

    city_lower = city.lower()
    if city_lower in weather_data:
        return {"city": city, **weather_data[city_lower]}
    else:
        return {"city": city, "temp": 70, "condition": "unknown"}


# Start the server
if __name__ == "__main__":
    mcp.run(transport="stdio")
