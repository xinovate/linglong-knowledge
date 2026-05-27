"""MCP Server for Linglong knowledge base."""

import logging

from starlette.applications import Starlette
from starlette.routing import Route

from mcp.server.fastmcp import FastMCP

from linglong.core.config import get_config
from linglong.mcp.tools import (
    execute_package,
    fetch_rss,
    generate_brief,
    get_template,
    list_entities,
    list_templates,
    read_entity,
    record_feedback,
    review_article,
    search_and_read,
    search_similar,
    search_web,
    search_wiki,
    update_entity,
    write_entity,
)

logger = logging.getLogger(__name__)

_TOOL_GROUPS: dict[str, list[object]] = {
    "ingest": [fetch_rss, generate_brief, execute_package, search_web, record_feedback],
    "knowledge": [
        search_wiki,
        search_similar,
        search_and_read,
        read_entity,
        write_entity,
        update_entity,
        list_entities,
        get_template,
        list_templates,
    ],
    "reviewer": [review_article],
}


def _register_tools(server: FastMCP, modules: list[str]) -> None:
    """Register MCP tools for the specified modules."""
    registered = 0
    for module in modules:
        tools = _TOOL_GROUPS.get(module, [])
        for tool in tools:
            server.tool()(tool)
            registered += 1
    logger.info("Registered %d tools from modules: %s", registered, modules)


def create_server() -> FastMCP:
    """Create a single FastMCP server (stdio mode)."""
    config = get_config()
    server = FastMCP(
        "linglong",
        host=config.mcp.host,
        port=config.mcp.port,
    )
    _register_tools(server, config.mcp.enabled_modules)
    return server


def create_http_app() -> Starlette:
    """Create a Starlette app with per-module MCP routes.

    Each enabled module gets its own FastMCP instance mounted at /mcp/{module}.
    E.g. enabled_modules=[ingest, knowledge] creates:
      /mcp/ingest    → ingest tools
      /mcp/knowledge → knowledge tools
    """
    config = get_config()
    routes: list[Route] = []

    for module in config.mcp.enabled_modules:
        tools = _TOOL_GROUPS.get(module, [])
        if not tools:
            continue
        server = FastMCP(
            f"linglong-{module}",
            streamable_http_path=f"/mcp/{module}",
        )
        for tool in tools:
            server.tool()(tool)
        app = server.streamable_http_app()
        routes.extend(app.routes)
        logger.info(
            "Module '%s': %d tools at /mcp/%s",
            module,
            len(tools),
            module,
        )

    return Starlette(routes=routes)
