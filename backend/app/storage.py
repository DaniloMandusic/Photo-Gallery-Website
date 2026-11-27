import os
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Self


@dataclass(frozen=True)
class Storage:
    database: Path
    media: Path

    @classmethod
    def from_environment(cls) -> Self:
        root = Path(__file__).resolve().parents[1] / "storage"
        return cls(Path(os.environ.get("GALLERY_DATABASE", root / "gallery.sqlite3")).resolve(),
                   Path(os.environ.get("GALLERY_MEDIA_ROOT", root / "media")).resolve())


@contextmanager
def connect(storage: Storage) -> Iterator[sqlite3.Connection]:
    db = sqlite3.connect(storage.database)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    try:
        with db:
            yield db
    finally:
        db.close()


def migrate(storage: Storage) -> None:
    storage.database.parent.mkdir(parents=True, exist_ok=True)
    storage.media.mkdir(parents=True, exist_ok=True)
    migrations = sorted((Path(__file__).parent / "migrations").glob("*.sql"))
    with connect(storage) as db:
        db.execute("BEGIN IMMEDIATE")
        version = db.execute("PRAGMA user_version").fetchone()[0]
        if version > len(migrations):
            raise RuntimeError("Database schema is newer than this application")
        for number, migration in enumerate(migrations, 1):
            if number > version:
                for statement in migration.read_text(encoding="utf-8").split(";"):
                    if statement.strip():
                        db.execute(statement)
                db.execute(f"PRAGMA user_version = {number}")


def media_path(root: Path, relative: str) -> Path:
    # Reject Windows drive/ADS syntax and alternate separators on every platform.
    if not relative or "\\" in relative or ":" in relative:
        raise ValueError("Invalid media path")
    path = Path(relative)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError("Invalid media path")
    resolved = (root / path).resolve()
    if not resolved.is_relative_to(root.resolve()):
        raise ValueError("Media path escapes storage")
    return resolved


if __name__ == "__main__":
    configured = Storage.from_environment()
    migrate(configured)
    print(f"Schema ready: {configured.database}\nMedia root: {configured.media}")
