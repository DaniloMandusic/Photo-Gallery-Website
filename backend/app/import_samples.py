"""Explicit one-time import; never invoked during application startup."""
import argparse
import hashlib
import shutil
import sqlite3
from pathlib import Path
from uuid import uuid4

from .sample_models import ROLES, SampleAlbum, sample_albums
from .storage import Storage, connect, media_path, migrate

IMPORT_NAME = "original-sample-albums-v1"


def require_unique_id(value: str, seen: set[str]) -> None:
    if value in seen:
        raise ValueError(f"Duplicate ID: {value}")
    seen.add(value)


def validate_samples(metadata: Path, source: Path) -> tuple[list[SampleAlbum], list[tuple[Path, str]]]:
    albums = sample_albums.validate_json(metadata.read_text(encoding="utf-8-sig"), strict=True)
    album_ids: set[str] = set()
    photo_ids: set[str] = set()
    files: list[tuple[Path, str]] = []
    for album in albums:
        require_unique_id(album.id, album_ids)
        for photo in album.photos:
            require_unique_id(photo.id, photo_ids)
            for role in ROLES:
                variant = photo.variant(role)
                expected = f'/photos/albums/{album.id}/{photo.id}-{role}.jpg'
                if variant.src != expected:
                    raise ValueError(f"Unexpected source path: {variant.src}")
                path = media_path(source, expected.removeprefix("/"))
                if not path.is_file():
                    raise ValueError(f"Missing source image: {path}")
                with path.open("rb") as image:
                    if image.read(2) != b"\xff\xd8":
                        raise ValueError(f"Not a JPEG: {path}")
                files.append((path, expected.removeprefix("/photos/")))
    if not files:
        raise ValueError("No image variants to import")
    return albums, files


def import_samples(storage: Storage, metadata: Path, source: Path) -> str:
    migrate(storage)
    with connect(storage) as db:
        db.execute("BEGIN IMMEDIATE")
        if db.execute("SELECT 1 FROM imports WHERE name = ?", (IMPORT_NAME,)).fetchone():
            return "Already imported; database and media left unchanged."
        if db.execute("SELECT 1 FROM albums LIMIT 1").fetchone():
            raise ValueError("Initial import requires an empty collection")
        albums, files = validate_samples(metadata, source)
        destination = media_path(storage.media, "albums")
        if destination.exists():
            raise ValueError(f"Destination already exists; inspect it before importing: {destination}")
        # Stage bytes before exposing rows. A crash after rename can leave an
        # orphan directory, which reruns refuse to overwrite.
        # TemporaryDirectory uses owner-only permissions on Windows. Renaming
        # its children preserves those ACLs and can lock out the backend user.
        # Inherit the configured media root's permissions instead.
        staging = media_path(storage.media, f"import-{uuid4().hex}")
        staging.mkdir()
        try:
            for original, relative in files:
                target = staging / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(original, target)
                if hashlib.sha256(original.read_bytes()).digest() != hashlib.sha256(target.read_bytes()).digest():
                    raise ValueError(f"Copy verification failed: {original}")
            for album_order, album in enumerate(albums):
                db.execute("INSERT INTO albums VALUES (?, ?, ?, 1)", (album.id, album.title, album_order))
                for photo_order, photo in enumerate(album.photos):
                    db.execute("INSERT INTO photos VALUES (?, ?, ?, ?)", (photo.id, album.id, photo.alt, photo_order))
                    for role in ROLES:
                        variant = photo.variant(role)
                        db.execute("INSERT INTO variants VALUES (?, ?, ?, ?, ?)", (photo.id, role, variant.src.removeprefix("/photos/"), variant.width, variant.height))
            db.execute("INSERT INTO imports VALUES (?)", (IMPORT_NAME,))
            (staging / "albums").rename(destination)
        finally:
            shutil.rmtree(staging)
        return f"Imported {len(albums)} albums, {sum(len(a.photos) for a in albums)} photos, {len(files)} verified image variants."


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--source-public", type=Path, required=True)
    args = parser.parse_args()
    try:
        print(import_samples(Storage.from_environment(), args.metadata.resolve(), args.source_public.resolve()))
    except (ValueError, OSError, sqlite3.Error) as error:
        parser.exit(1, f"Import failed: {error}\n")


if __name__ == "__main__":
    main()
