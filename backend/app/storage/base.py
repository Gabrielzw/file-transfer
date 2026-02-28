from __future__ import annotations

from dataclasses import dataclass
from typing import BinaryIO, Protocol


@dataclass(frozen=True)
class StoredFile:
    stored_name: str
    relative_path: str
    size_bytes: int


class Storage(Protocol):
    def save(
        self,
        *,
        source: BinaryIO,
        original_filename: str,
        max_bytes: int,
    ) -> StoredFile: ...

    def delete(self, *, relative_path: str) -> None: ...

    def resolve_path(self, *, relative_path: str) -> str: ...
