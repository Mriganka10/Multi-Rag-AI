import base64
import binascii
import secrets
from dataclasses import dataclass

from fastapi import Request
from fastapi.responses import Response

from app.core.config import settings


@dataclass(frozen=True)
class CurrentUser:
    username: str
    role: str


def auth_challenge() -> Response:
    return Response(
        status_code=401,
        headers={"WWW-Authenticate": 'Basic realm="CA Agentic AI RAG"'},
        content="Authentication required",
    )


def authenticate_request(request: Request) -> CurrentUser | None:
    if not settings.auth_enabled:
        return CurrentUser(username="local-dev", role="admin")

    if not settings.auth_password:
        return None

    authorization = request.headers.get("authorization", "")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "basic" or not token:
        return None

    try:
        decoded = base64.b64decode(token).decode("utf-8")
    except (binascii.Error, UnicodeDecodeError):
        return None

    username, separator, password = decoded.partition(":")
    if not separator:
        return None

    username_ok = secrets.compare_digest(username, settings.auth_username)
    password_ok = secrets.compare_digest(password, settings.auth_password)
    if not (username_ok and password_ok):
        return None

    return CurrentUser(username=username, role=settings.auth_default_role)


def is_reviewer(user: CurrentUser | None) -> bool:
    return bool(user and user.role in {"admin", "reviewer"})
