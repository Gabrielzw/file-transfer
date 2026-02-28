from __future__ import annotations

from collections.abc import Generator
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.security import InvalidTokenError, assert_admin_token, decode_token
from app.core.settings import Settings, get_settings
from app.db.session import Database
from app.storage import Storage


def settings_dep() -> Settings:
    return get_settings()


SettingsDep = Annotated[Settings, Depends(settings_dep)]


def db_dep(request: Request) -> Generator[Session, None, None]:
    database: Database = request.app.state.database
    with database.sessionmaker() as session:
        yield session


DbDep = Annotated[Session, Depends(db_dep)]


def storage_dep(request: Request) -> Storage:
    return request.app.state.storage


StorageDep = Annotated[Storage, Depends(storage_dep)]


def require_admin(
    *,
    settings: SettingsDep,
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
) -> str:
    if not authorization:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未登录")

    parts = authorization.split(" ", maxsplit=1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未登录")

    token = parts[1]
    try:
        payload = decode_token(secret=settings.jwt_secret.get_secret_value(), token=token)
        assert_admin_token(payload=payload)
    except InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未登录")

    return payload.sub


AdminDep = Annotated[str, Depends(require_admin)]
