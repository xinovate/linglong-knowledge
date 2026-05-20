"""Linglong MCP Server package."""

from linglong.mcp.server import mcp


def main() -> None:
    """Run the MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
