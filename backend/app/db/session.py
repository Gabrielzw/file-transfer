from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker


@dataclass(frozen=True)
class Database:
    engine: Engine
    sessionmaker: sessionmaker[Session]


def _ensure_parent_dir(*, file_path: str) -> None:
    Path(file_path).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)


def _build_sqlite_url(*, db_path: str) -> str:
    abs_path = Path(db_path).expanduser().resolve()
    return f"sqlite+pysqlite:///{abs_path}"


def create_sqlite_database(*, db_path: str) -> Database:
    _ensure_parent_dir(file_path=db_path)
    engine = create_engine(
        _build_sqlite_url(db_path=db_path),
        connect_args={"check_same_thread": False},
        pool_pre_ping=True,
    )
    maker = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)
    return Database(engine=engine, sessionmaker=maker)
