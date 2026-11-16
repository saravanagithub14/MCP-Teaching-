"""A second, unrelated MCP server. Same protocol, different job."""
from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

mcp = MCPServer("notes")
NOTES: list[str] = []  # state lives inside this server process


@mcp.tool()
def add_note(text: str) -> str:
    """Save a short note."""
    if not text.strip():
        raise ToolError("note text is empty")
    NOTES.append(text)
    return f"saved note #{len(NOTES)}"


@mcp.tool()
def list_notes() -> list[str]:
    """List every note."""
    return NOTES


@mcp.resource("notes://count")
def count() -> str:
    """How many notes exist."""
    return str(len(NOTES))


if __name__ == "__main__":
    mcp.run(transport="stdio")
