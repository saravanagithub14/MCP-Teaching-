"""Notes server, now with tool annotations.

Annotations are hints a server attaches to each tool, saying what kind of
thing it does. The host uses them to decide what needs the user's approval
before an LLM is allowed to run it.

    read_only_hint=True    -> only looks at data, safe to run without asking
    destructive_hint=True  -> may delete or overwrite data, always ask first
"""
from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations

mcp = MCPServer("notes")
NOTES: list[str] = []  # state lives inside this server process


@mcp.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False))
def add_note(text: str) -> str:
    """Save a short note."""
    if not text.strip():
        raise ToolError("note text is empty")
    NOTES.append(text)
    return f"saved note #{len(NOTES)}"


@mcp.tool(annotations=ToolAnnotations(read_only_hint=True))
def list_notes() -> list[str]:
    """List every note."""
    return NOTES


@mcp.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=True))
def clear_notes() -> str:
    """Delete every note. This cannot be undone."""
    count = len(NOTES)
    NOTES.clear()
    return f"deleted {count} note(s)"


@mcp.resource("notes://count")
def count() -> str:
    """How many notes exist."""
    return str(len(NOTES))


if __name__ == "__main__":
    mcp.run(transport="stdio")
