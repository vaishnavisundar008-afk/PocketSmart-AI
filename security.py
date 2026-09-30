import base64
import hashlib
import hmac
import json
import secrets
import time
from datetime import UTC, datetime, timedelta

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer

from app import database
from app.config import settings


ALGORITHM = "HS256"
SESSION_COOKIE = "pocketsmart_session"
TOKEN_TTL_MINUTES = 60 * 24 * 7
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token", auto_error=False)


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    derived = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=2**14, r=8, p=1, dklen=32)
    return f"scrypt$16384$8$1${_base64url(salt)}${_base64url(derived)}"


def verify_password(password: str, password_hash: str) -> bool:
    try:
        algorithm, cost, block_size, parallelism, salt_text, expected = password_hash.split("$")
        if algorithm != "scrypt" or (cost, block_size, parallelism) != ("16384", "8", "1"):
            return False
        salt = _decode_base64url(salt_text)
        actual = hashlib.scrypt(
            password.encode("utf-8"), salt=salt, n=int(cost), r=int(block_size), p=int(parallelism), dklen=32
        )
        return hmac.compare_digest(_base64url(actual), expected)
    except (ValueError, TypeError, MemoryError):
        return False


def create_access_token(user_id: str) -> str:
    expires = datetime.now(UTC) + timedelta(minutes=TOKEN_TTL_MINUTES)
    header = _base64url(json.dumps({"alg": ALGORITHM, "typ": "JWT"}, separators=(",", ":")).encode())
    payload = _base64url(json.dumps({"sub": user_id, "exp": int(expires.timestamp())}, separators=(",", ":")).encode())
    signing_input = f"{header}.{payload}"
    signature = _base64url(hmac.new(settings.secret_key.encode(), signing_input.encode(), hashlib.sha256).digest())
    return f"{signing_input}.{signature}"


def issue_session_cookie(response, user_id: str) -> None:
    response.set_cookie(
        SESSION_COOKIE,
        create_access_token(user_id),
        max_age=TOKEN_TTL_MINUTES * 60,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
    )


def get_current_user(
    request: Request,
    bearer_token: str | None = Depends(oauth2_scheme),
) -> dict | None:
    token = bearer_token or request.cookies.get(SESSION_COOKIE)
    if not token:
        return None
    try:
        header_part, payload_part, signature_part = token.split(".")
        signing_input = f"{header_part}.{payload_part}"
        expected = _base64url(hmac.new(settings.secret_key.encode(), signing_input.encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(signature_part, expected):
            return None
        header = json.loads(_decode_base64url(header_part))
        if header.get("alg") != ALGORITHM:
            return None
        payload = json.loads(_decode_base64url(payload_part))
        if not isinstance(payload.get("exp"), int) or payload["exp"] <= time.time():
            return None
        user_id = payload.get("sub")
        if not isinstance(user_id, str):
            return None
    except (ValueError, TypeError, json.JSONDecodeError):
        return None
    user = database.get_user_by_id(user_id)
    if not user:
        return None
    user.pop("password_hash", None)
    return user


def require_user(user: dict | None = Depends(get_current_user)) -> dict:
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sign in to use this feature.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def require_csrf(request: Request) -> None:
    if request.headers.get("authorization", "").lower().startswith("bearer "):
        return
    cookie_token = request.cookies.get("pocketsmart_csrf", "")
    header_token = request.headers.get("x-csrf-token", "")
    import secrets

    if not cookie_token or not header_token or not secrets.compare_digest(cookie_token, header_token):
        raise HTTPException(status_code=403, detail="Refresh the page and try again.")


def _base64url(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _decode_base64url(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))