"""MCP Server for Linglong knowledge base."""

import logging
from contextlib import asynccontextmanager

from starlette.applications import Starlette
from starlette.routing import Mount

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.server import TransportSecuritySettings

from linglong.core.config import get_config
from linglong.mcp.tools import (
    get_template,
    list_entities,
    list_templates,
    read_entity,
    rebuild,
    search_and_read,
    search_similar,
    search_wiki,
    update_entity,
    write_entity,
)

logger = logging.getLogger(__name__)

_TOOL_GROUPS: dict[str, list[object]] = {
    "knowledge": [
        search_wiki,
        search_similar,
        search_and_read,
        read_entity,
        write_entity,
        update_entity,
        rebuild,
        list_entities,
        get_template,
        list_templates,
    ],
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

    Each enabled module gets its own FastMCP instance. We extract each
    app's route (bound to /mcp/{module}) and lifespan, then compose
    them into a single Starlette app that runs all lifespans.
    """
    config = get_config()
    routes = []
    lifespans = []

    for module in config.mcp.enabled_modules:
        tools = _TOOL_GROUPS.get(module, [])
        if not tools:
            continue
        allowed_hosts = []
        if config.mcp.allowed_hosts:
            allowed_hosts = config.mcp.allowed_hosts

        server = FastMCP(
            f"linglong-{module}",
            streamable_http_path=f"/mcp/{module}",
            transport_security=TransportSecuritySettings(
                allowed_hosts=allowed_hosts,
            ),
        )
        for tool in tools:
            server.tool()(tool)
        app = server.streamable_http_app()
        routes.extend(app.routes)
        if app.router.lifespan_context:
            lifespans.append(app.router.lifespan_context)
        logger.info(
            "Module '%s': %d tools at /mcp/%s",
            module,
            len(tools),
            module,
        )

    @asynccontextmanager
    async def _combined_lifespan(app):
        import contextlib

        async with contextlib.AsyncExitStack() as stack:
            for ls in lifespans:
                await stack.enter_async_context(ls(app))
            yield

    return Starlette(routes=routes, lifespan=_combined_lifespan)
