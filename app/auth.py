import hmac
from urllib.parse import parse_qs

from starlette.responses import JSONResponse

from app.config import AUTH_TOKEN


class MCPAuthMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http" and AUTH_TOKEN and scope["path"].startswith("/mcp"):
            headers = dict(scope["headers"])
            auth = headers.get(b"authorization", b"").decode()
            if auth.startswith("Bearer "):
                provided = auth[len("Bearer "):]
            else:  # alternativa: /mcp?token=...
                query = parse_qs(scope["query_string"].decode())
                provided = query.get("token", [""])[0]

            if not hmac.compare_digest(provided.encode(), AUTH_TOKEN.encode()):
                response = JSONResponse({"detail": "Invalid or missing token"}, status_code=401)
                await response(scope, receive, send)
                return
        await self.app(scope, receive, send)