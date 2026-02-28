from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
import jwt

from app.core.constants import ADMIN_TOKEN_TYPE, DOWNLOAD_TOKEN_TYPE


class InvalidTokenError(Exception):
    pass


@dataclass(frozen=True)
class TokenPayload:
    typ: str
    sub: str
    exp: datetime
    extra: dict[str, Any]


def verify_admin_password(*, expected: str, provided: str) -> bool:
    return secrets.compare_digest(expected, provided)


def hash_password(*, password: str) -> str:
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(*, password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def create_token(
    *,
    secret: str,
    token_type: str,
    subject: str,
    expires_in_seconds: int,
    extra: dict[str, Any] | None = None,
) -> str:
    now = datetime.now(timezone.utc)
    exp = now + timedelta(seconds=expires_in_seconds)
    payload: dict[str, Any] = {
        "typ": token_type,
        "sub": subject,
        "exp": exp,
        "iat": now,
        **(extra or {}),
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def decode_token(*, secret: str, token: str) -> TokenPayload:
    try:
        raw = jwt.decode(token, secret, algorithms=["HS256"])
    except jwt.PyJWTError as exc:  # pragma: no cover
        raise InvalidTokenError(str(exc)) from exc

    token_type = raw.get("typ")
    subject = raw.get("sub")
    exp = raw.get("exp")
    if not isinstance(token_type, str) or not isinstance(subject, str):
        raise InvalidTokenError("Invalid payload")

    if isinstance(exp, int):
        exp_dt = datetime.fromtimestamp(exp, tz=timezone.utc)
    elif isinstance(exp, float):
        exp_dt = datetime.fromtimestamp(int(exp), tz=timezone.utc)
    else:
        raise InvalidTokenError("Invalid exp")

    extra = {k: v for k, v in raw.items() if k not in {"typ", "sub", "exp"}}
    return TokenPayload(typ=token_type, sub=subject, exp=exp_dt, extra=extra)


def assert_token_type(*, payload: TokenPayload, expected: str) -> None:
    if payload.typ != expected:
        raise InvalidTokenError("Unexpected token type")


def assert_admin_token(*, payload: TokenPayload) -> None:
    assert_token_type(payload=payload, expected=ADMIN_TOKEN_TYPE)


def assert_download_token(*, payload: TokenPayload) -> None:
    assert_token_type(payload=payload, expected=DOWNLOAD_TOKEN_TYPE)
