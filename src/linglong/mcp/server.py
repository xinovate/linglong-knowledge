"""MCP Server for Linglong knowledge base."""

from mcp.server.fastmcp import FastMCP

from linglong.mcp.tools import (
    execute_package,
    fetch_rss,
    get_template,
    list_entities,
    list_templates,
    read_entity,
    record_feedback,
    search_and_read,
    search_similar,
    search_wiki,
    update_entity,
    write_entity,
)

mcp = FastMCP("linglong")

mcp.tool()(search_wiki)
mcp.tool()(search_similar)
mcp.tool()(search_and_read)
mcp.tool()(read_entity)
mcp.tool()(write_entity)
mcp.tool()(update_entity)
mcp.tool()(list_entities)
mcp.tool()(get_template)
mcp.tool()(list_templates)
mcp.tool()(fetch_rss)
mcp.tool()(record_feedback)
mcp.tool()(execute_package)
