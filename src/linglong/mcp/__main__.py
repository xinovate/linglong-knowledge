"""Entry point for python -m linglong.mcp."""

import logging

from linglong.core.config import get_config
from linglong.mcp.server import create_http_app, create_server

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main() -> None:
    """Run the MCP server."""
    config = get_config()
    transport = config.mcp.transport

    if transport == "stdio":
        server = create_server()
        logger.info("Starting MCP server (stdio)")
        server.run(transport="stdio")
    else:
        logger.info(
            "Starting MCP server (%s) on %s:%d",
            transport,
            config.mcp.host,
            config.mcp.port,
        )
        _run_http(config)


def _run_http(config) -> None:
    """Run HTTP server with per-module routing and optional auth."""
    import anyio

    async def _serve():
        import uvicorn

        app = create_http_app()

        if config.mcp.auth_token:
            from linglong.mcp._auth import TokenAuthMiddleware

            app.add_middleware(TokenAuthMiddleware, expected_token=config.mcp.auth_token)
            logger.info("Token auth enabled")

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
