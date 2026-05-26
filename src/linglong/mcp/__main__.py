"""Entry point for python -m linglong.mcp."""

import logging

from linglong.core.config import get_config
from linglong.mcp.server import create_server

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main() -> None:
    """Run the MCP server."""
    config = get_config()
    server = create_server()
    transport = config.mcp.transport

    if transport == "stdio":
        logger.info("Starting MCP server (stdio)")
        server.run(transport="stdio")
    else:
        logger.info(
            "Starting MCP server (%s) on %s:%d",
            transport,
            config.mcp.host,
            config.mcp.port,
        )
        if config.mcp.auth_token:
            _run_with_auth(server, config)
        else:
            server.run(transport=transport)


def _run_with_auth(server, config) -> None:
    """Run HTTP server with Bearer token authentication."""
    import anyio

    async def _serve():
        import uvicorn

        from linglong.mcp._auth import TokenAuthMiddleware

        app = server.streamable_http_app()
        app.add_middleware(TokenAuthMiddleware, expected_token=config.mcp.auth_token)
        uv_config = uvicorn.Config(
            app,
            host=config.mcp.host,
            port=config.mcp.port,
            log_level="info",
        )
        await uvicorn.Server(uv_config).serve()

    anyio.run(_serve)


if __name__ == "__main__":
    main()
