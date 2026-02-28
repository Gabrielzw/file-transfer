from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO
from uuid import uuid4

from app.core.constants import FILE_IO_CHUNK_BYTES
from app.storage.base import StoredFile, Storage
from app.storage.errors import FileTooLargeError, StorageFileNotFoundError


@dataclass(frozen=True)
class LocalStorage(Storage):
    root_dir: str

    def __post_init__(self) -> None:
        Path(self.root_dir).expanduser().resolve().mkdir(parents=True, exist_ok=True)

    def save(
        self,
        *,
        source: BinaryIO,
        original_filename: str,
        max_bytes: int,
    ) -> StoredFile:
        suffix = Path(original_filename).suffix
        stored_name = f"{uuid4()}{suffix}"
        relative_path = stored_name
        abs_path = Path(self.resolve_path(relative_path=relative_path))

        size_bytes = 0
        try:
            with abs_path.open("wb") as out:
                while True:
                    chunk = source.read(FILE_IO_CHUNK_BYTES)
                    if not chunk:
                        break
                    size_bytes += len(chunk)
                    if size_bytes > max_bytes:
                        raise FileTooLargeError(f"File exceeds max bytes: {max_bytes}")
                    out.write(chunk)
        except Exception:
            abs_path.unlink(missing_ok=True)
            raise

        return StoredFile(
            stored_name=stored_name,
            relative_path=relative_path,
            size_bytes=size_bytes,
        )

    def delete(self, *, relative_path: str) -> None:
        abs_path = Path(self.resolve_path(relative_path=relative_path))
        if not abs_path.exists():
            raise StorageFileNotFoundError(relative_path)
        abs_path.unlink()

    def resolve_path(self, *, relative_path: str) -> str:
        return str(Path(self.root_dir).expanduser().resolve() / relative_path)
