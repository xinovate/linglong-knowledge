"""Token authentication middleware for MCP HTTP server."""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse


class TokenAuthMiddleware(BaseHTTPMiddleware):
    """Reject requests without a valid Bearer token."""

    def __init__(self, app, expected_token: str):
        super().__init__(app)
        self.expected_token = expected_token

    async def dispatch(self, request: Request, call_next):
        auth = request.headers.get("Authorization", "")
        if auth != f"Bearer {self.expected_token}":
            return JSONResponse(status_code=401, content={"error": "Unauthorized"})
        return await call_next(request)
