"""Entry point for python -m linglong.mcp."""

import logging

from linglong.core.config import get_config
from linglong.mcp.server import create_http_app, create_server

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _setup_file_logging(log_file) -> None:
    """Add file handler if log_file is configured."""
    if not log_file:
        return
    log_file.parent.mkdir(parents=True, exist_ok=True)
    handler = logging.FileHandler(log_file, encoding="utf-8")
    handler.setFormatter(logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s: %(message)s"
    ))
    logging.getLogger().addHandler(handler)


def main() -> None:
    """Run the MCP server."""
    config = get_config()
    _setup_file_logging(config.log_file)
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

        if config.mcp.auth_token or config.mcp.redis_url:
            from linglong.mcp._auth import TokenAuthMiddleware

            app.add_middleware(
                TokenAuthMiddleware,
                expected_token=config.mcp.auth_token or "",
                redis_url=config.mcp.redis_url,
            )
            if config.mcp.redis_url:
                logger.info("Token auth enabled (Redis)")
            else:
                logger.info("Token auth enabled (static)")

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
