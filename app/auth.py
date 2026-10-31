from contextvars import ContextVar
from urllib.parse import parse_qs

from starlette.responses import JSONResponse

from app import crud
from app.database import SessionLocal

# id del usuario autenticado en la petición actual
current_user_id: ContextVar[int | None] = ContextVar("current_user_id", default=None)


def _extract_token(scope) -> str:
    headers = dict(scope["headers"])
    auth = headers.get(b"authorization", b"").decode()
    if auth.startswith("Bearer "):
        return auth[len("Bearer "):].strip()
    query = parse_qs(scope["query_string"].decode())
    return query.get("token", [""])[0]  # alternativa: /mcp?token=...


class MCPAuthMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or not scope["path"].startswith("/mcp"):
            await self.app(scope, receive, send)
            return

        token = _extract_token(scope)
        with SessionLocal() as db:
            user = crud.get_user_by_token(db, token) if token else None

        if not user:
            response = JSONResponse({"detail": "Invalid or missing token"}, status_code=401)
            await response(scope, receive, send)
            return

        reset = current_user_id.set(user.id)
        try:
            await self.app(scope, receive, send)
        finally:
            current_user_id.reset(reset)