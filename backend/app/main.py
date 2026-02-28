from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.settings import get_settings
from app.db.base import Base
from app.db.session import create_sqlite_database
from app.models import File, ShareDownloadToken, ShareLink  # noqa: F401
from app.routers import auth, files, share
from app.storage.local import LocalStorage


def _split_csv(value: str) -> list[str]:
    return [v.strip() for v in value.split(",") if v.strip()]


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="file-transfer")

    if settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=_split_csv(settings.cors_origins),
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    @app.on_event("startup")
    def _startup() -> None:
        database = create_sqlite_database(db_path=settings.db_path)
        Base.metadata.create_all(bind=database.engine)
        app.state.database = database
        app.state.storage = LocalStorage(root_dir=settings.storage_dir)

    app.include_router(auth.router, prefix="/api", tags=["auth"])
    app.include_router(files.router, prefix="/api", tags=["files"])
    app.include_router(share.router, prefix="/api", tags=["share"])
    return app


app = create_app()
