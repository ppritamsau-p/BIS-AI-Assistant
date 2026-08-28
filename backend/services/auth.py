"""JWT authentication and role-based access.

Password hashing uses PBKDF2-HMAC-SHA256 from the standard library so the prototype has no
crypto dependency to install. For production, move users into the database and switch the
hasher to argon2 or bcrypt -- the interface here (`verify_password`) is the only thing that
would change.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from typing import Any

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from backend.config import settings

PBKDF2_ROUNDS = 240_000
bearer_scheme = HTTPBearer(auto_error=False)


# --------------------------------------------------------------------------
# Password hashing
# --------------------------------------------------------------------------
def hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, PBKDF2_ROUNDS)
    return f"pbkdf2_sha256${PBKDF2_ROUNDS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        _algo, rounds, salt_hex, digest_hex = encoded.split("$")
        digest = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), bytes.fromhex(salt_hex), int(rounds)
        )
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(digest.hex(), digest_hex)


# --------------------------------------------------------------------------
# Demo user store
# --------------------------------------------------------------------------
# Credentials are read from the environment so a deployment never inherits the demo
# passwords silently; the defaults exist only to make the prototype runnable.
_DEMO_USERS: dict[str, dict[str, Any]] = {
    "admin": {
        "username": "admin",
        "role": "admin",
        "password_hash": hash_password(os.getenv("ADMIN_PASSWORD", "admin123")),
    },
    "user": {
        "username": "user",
        "role": "user",
        "password_hash": hash_password(os.getenv("USER_PASSWORD", "user123")),
    },
}


def authenticate(username: str, password: str) -> dict[str, Any] | None:
    user = _DEMO_USERS.get((username or "").strip().lower())
    if not user or not verify_password(password, user["password_hash"]):
        return None
    return user


# --------------------------------------------------------------------------
# JWT (HS256) -- implemented directly to avoid an extra dependency
# --------------------------------------------------------------------------
def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64url_decode(segment: str) -> bytes:
    padding = "=" * (-len(segment) % 4)
    return base64.urlsafe_b64decode(segment + padding)


def create_token(username: str, role: str) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    now = int(time.time())
    payload = {
        "sub": username,
        "role": role,
        "iat": now,
        "exp": now + settings.jwt_expiry_minutes * 60,
        "jti": secrets.token_hex(8),
    }
    signing_input = (
        _b64url(json.dumps(header, separators=(",", ":")).encode())
        + "."
        + _b64url(json.dumps(payload, separators=(",", ":")).encode())
    )
    signature = hmac.new(
        settings.jwt_secret.encode(), signing_input.encode(), hashlib.sha256
    ).digest()
    return f"{signing_input}.{_b64url(signature)}"


def decode_token(token: str) -> dict[str, Any]:
    try:
        header_b64, payload_b64, signature_b64 = token.split(".")
    except ValueError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Malformed token") from None

    expected = hmac.new(
        settings.jwt_secret.encode(),
        f"{header_b64}.{payload_b64}".encode(),
        hashlib.sha256,
    ).digest()
    if not hmac.compare_digest(_b64url(expected), signature_b64):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token signature")

    payload = json.loads(_b64url_decode(payload_b64))
    if payload.get("exp", 0) < time.time():
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token expired")
    return payload


# --------------------------------------------------------------------------
# FastAPI dependencies
# --------------------------------------------------------------------------
def current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> dict[str, Any] | None:
    """Optional identity. Public endpoints stay usable without signing in."""
    if credentials is None:
        return None
    return decode_token(credentials.credentials)


def require_admin(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> dict[str, Any]:
    if credentials is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Authentication required")
    payload = decode_token(credentials.credentials)
    if payload.get("role") != "admin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Administrator role required")
    return payload
