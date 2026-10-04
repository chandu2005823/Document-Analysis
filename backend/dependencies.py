import base64
import binascii
import hashlib
import hmac
import json
import os
import secrets
import time

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from database.access_control import AuthorizationError, require_login, require_project_access


TOKEN_TTL_SECONDS = 3600
_TOKEN_SECRET = os.environ.get("AUTOARCH_API_SECRET")
if _TOKEN_SECRET:
    if len(_TOKEN_SECRET.encode("utf-8")) < 32:
        raise RuntimeError("AUTOARCH_API_SECRET must be at least 32 bytes.")
    _TOKEN_SECRET = _TOKEN_SECRET.encode("utf-8")
else:
    _TOKEN_SECRET = secrets.token_bytes(32)

_bearer = HTTPBearer(auto_error=False)


def _encode_segment(value):
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _decode_segment(value):
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def create_access_token(user_id, *, now=None):
    payload = json.dumps(
        {"sub": int(user_id), "exp": int(now or time.time()) + TOKEN_TTL_SECONDS},
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    encoded_payload = _encode_segment(payload)
    signature = hmac.new(
        _TOKEN_SECRET, encoded_payload.encode("ascii"), hashlib.sha256
    ).digest()
    return f"{encoded_payload}.{_encode_segment(signature)}"


def decode_access_token(token, *, now=None):
    try:
        encoded_payload, encoded_signature = token.split(".", 1)
        expected_signature = hmac.new(
            _TOKEN_SECRET, encoded_payload.encode("ascii"), hashlib.sha256
        ).digest()
        supplied_signature = _decode_segment(encoded_signature)
        if not hmac.compare_digest(expected_signature, supplied_signature):
            return None
        payload = json.loads(_decode_segment(encoded_payload))
        user_id = int(payload["sub"])
        if int(payload["exp"]) <= int(now or time.time()):
            return None
        return user_id
    except (
        AttributeError,
        TypeError,
        ValueError,
        KeyError,
        binascii.Error,
        json.JSONDecodeError,
    ):
        return None


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
):
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "unauthenticated", "message": "Bearer authentication is required."},
            headers={"WWW-Authenticate": "Bearer"},
        )
    if len(credentials.credentials) > 4096:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "invalid_token", "message": "The access token is invalid or expired."},
            headers={"WWW-Authenticate": "Bearer"},
        )
    user_id = decode_access_token(credentials.credentials)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "invalid_token", "message": "The access token is invalid or expired."},
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        return require_login(user_id)
    except AuthorizationError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "inactive_account", "message": "The account is inactive or unavailable."},
            headers={"WWW-Authenticate": "Bearer"},
        ) from None


def get_authorized_project(project_id: int, current_user=Depends(get_current_user)):
    try:
        return require_project_access(current_user["id"], project_id)
    except AuthorizationError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "project_forbidden", "message": "You are not authorized for this project."},
        ) from None


def require_project_roles(project, *roles):
    if project["role"] not in roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "role_forbidden", "message": "Your project role cannot perform this operation."},
        )
    return project