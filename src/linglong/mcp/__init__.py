"""Linglong MCP Server package."""

from linglong.mcp.server import create_server


def main() -> None:
    """Run the MCP server (CLI entry point)."""
    from linglong.mcp.__main__ import main as _main

    _main()


if __name__ == "__main__":
    main()
