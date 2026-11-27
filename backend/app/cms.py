"""Local-only album mutations. Authentication is intentionally deferred."""
import hashlib
import logging
import shutil
import sqlite3
import warnings
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException, Request
from PIL import Image, ImageOps, UnidentifiedImageError
from pydantic import BaseModel, ConfigDict
from starlette.concurrency import run_in_threadpool
from starlette.datastructures import UploadFile

from .storage import Storage, connect, media_path

MAX_FILES = 30
MAX_FILE_BYTES = 20 * 1024 * 1024
MAX_TOTAL_BYTES = 100 * 1024 * 1024
MAX_REQUEST_BYTES = MAX_TOTAL_BYTES + 1024 * 1024
MAX_PIXELS = 40_000_000
ROLES = {"thumbnail": 240, "preview": 960, "viewer": 1920}
logger = logging.getLogger(__name__)


class UploadLimit:
    """Bound the incoming multipart body, including requests without Content-Length."""
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["path"] != "/api/admin/albums" or scope["method"] != "POST":
            return await self.app(scope, receive, send)
        total = 0

        async def limited_receive():
            nonlocal total
            message = await receive()
            total += len(message.get("body", b""))
            if total > MAX_REQUEST_BYTES:
                raise HTTPException(413, "Upload exceeds the 100 MiB total limit.")
            return message

        await self.app(scope, limited_receive, send)


class AlbumOrder(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")
    ids: list[str]
    previous: list[str]


def process_photo(upload: UploadFile, directory: Path, photo_id: str) -> list[tuple]:
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            upload.file.seek(0)
            with Image.open(upload.file) as original:
                if original.format != "JPEG":
                    raise ValueError("Only JPEG photos are supported.")
                if original.width * original.height > MAX_PIXELS:
                    raise ValueError("Each photo must be at most 40 million pixels.")
                original.load()
                image = ImageOps.exif_transpose(original).convert("RGB")
            image.info.clear()
            variants = []
            for role, size in ROLES.items():
                variant = image.copy()
                variant.thumbnail((size, size), Image.Resampling.LANCZOS)
                name = f"{photo_id}-{role}.jpg"
                variant.save(directory / name, "JPEG", quality=88)
                variants.append((photo_id, role, name, variant.width, variant.height))
            return variants
    except (UnidentifiedImageError, Image.DecompressionBombError, Image.DecompressionBombWarning, ValueError) as error:
        raise HTTPException(422, str(error) if isinstance(error, ValueError) else "Invalid or oversized JPEG photo.") from None
    except OSError:
        # Decoder failures and filesystem failures both leave the album uncommitted.
        raise HTTPException(422, "Could not decode or save a JPEG. Check the photos and available disk space.") from None


def create_album(storage: Storage, title: str, request_id: str, uploads: list[UploadFile]) -> dict:
    title = title.strip()
    if not title or len(title) > 120:
        raise HTTPException(422, "Enter an album title of 1–120 characters.")
    try:
        request_id = str(UUID(request_id))
    except ValueError:
        raise HTTPException(422, "Invalid creation request ID.") from None
    if not 1 <= len(uploads) <= MAX_FILES:
        raise HTTPException(422, "Choose 1–30 JPEG photos.")
    digest = hashlib.sha256(title.encode())
    total = 0
    for upload in uploads:
        size = 0
        file_hash = hashlib.sha256()
        while chunk := upload.file.read(1024 * 1024):
            size += len(chunk)
            total += len(chunk)
            if size > MAX_FILE_BYTES or total > MAX_TOTAL_BYTES:
                raise HTTPException(413, "Limit: 20 MiB per photo and 100 MiB total.")
            file_hash.update(chunk)
        if not size:
            raise HTTPException(422, "Empty photos are not supported.")
        digest.update(file_hash.digest())
    fingerprint = digest.hexdigest()
    # Serialize mutations, including the receipt check, to make concurrent retries safe.
    staging = media_path(storage.media, f"staging-{uuid4().hex}")
    destination = None
    committed = False
    try:
        with connect(storage) as db:
            db.execute("BEGIN IMMEDIATE")
            receipt = db.execute("SELECT * FROM creations WHERE request_id = ?", (request_id,)).fetchone()
            if receipt:
                if receipt["fingerprint"] != fingerprint:
                    raise HTTPException(409, "This request ID was already used for different content.")
                if not db.execute("SELECT 1 FROM albums WHERE id = ?", (receipt["album_id"],)).fetchone():
                    raise HTTPException(409, "This album was already created and later deleted. Start a new album.")
                return {"id": receipt["album_id"]}
            album_id = uuid4().hex
            destination = media_path(storage.media, f"albums/{album_id}")
            staging.mkdir()  # Ordinary mkdir preserves inherited Windows permissions.
            photos = []
            variants = []
            for position, upload in enumerate(uploads):
                photo_id = uuid4().hex
                photos.append((photo_id, album_id, f"{title} — photo {position + 1}", position))
                for pid, role, name, width, height in process_photo(upload, staging, photo_id):
                    variants.append((pid, role, f"albums/{album_id}/{name}", width, height))
            position = db.execute("SELECT coalesce(max(position), -1) + 1 FROM albums").fetchone()[0]
            db.execute("INSERT INTO albums VALUES (?, ?, ?, 1)", (album_id, title, position))
            db.executemany("INSERT INTO photos VALUES (?, ?, ?, ?)", photos)
            db.executemany("INSERT INTO variants VALUES (?, ?, ?, ?, ?)", variants)
            db.execute("INSERT INTO creations VALUES (?, ?, ?)", (request_id, fingerprint, album_id))
            destination.parent.mkdir(exist_ok=True)
            staging.rename(destination)
        committed = True
        return {"id": album_id}
    finally:
        # A process crash between rename and commit may leave private orphan files.
        for path in (staging, destination if not committed else None):
            if path is not None and path.exists():
                try:
                    shutil.rmtree(path)
                except OSError:
                    logger.exception("Private upload cleanup failed: %s", path)


def delete_album(storage: Storage, album_id: str) -> dict:
    with connect(storage) as db:
        db.execute("BEGIN IMMEDIATE")
        album = db.execute("SELECT published FROM albums WHERE id = ?", (album_id,)).fetchone()
        if album and not album["published"]:
            raise HTTPException(404, "Album not found.")
        db.execute("INSERT OR IGNORE INTO media_cleanup SELECT ?, v.path FROM variants v "
                   "JOIN photos p ON p.id = v.photo_id WHERE p.album_id = ?", (album_id, album_id))
        db.execute("DELETE FROM albums WHERE id = ?", (album_id,))
    # Commit revocation first. Keep durable cleanup entries until files are removed.
    failed = 0
    with connect(storage) as db:
        db.execute("BEGIN IMMEDIATE")
        paths = db.execute("SELECT path FROM media_cleanup WHERE album_id = ?", (album_id,)).fetchall()
        for row in paths:
            try:
                path = media_path(storage.media, row["path"])
                if path.suffix.lower() not in (".jpg", ".jpeg") or path == storage.database.resolve():
                    raise ValueError("Not an owned JPEG")
                # Resolve aliases too: never delete a file still referenced by another album.
                for reference in db.execute("SELECT path FROM variants"):
                    if media_path(storage.media, reference["path"]) == path:
                        raise ValueError("File still referenced")
                path.unlink(missing_ok=True)
                db.execute("DELETE FROM media_cleanup WHERE path = ?", (row["path"],))
                try:
                    path.parent.rmdir()  # Only an empty directory; never recursive.
                except OSError:
                    pass
            except (OSError, ValueError):
                failed += 1
    return {"deleted": True, "cleanup_pending": failed,
            "message": "Album removed. Some stored files could not be removed; retry cleanup." if failed else "Album deleted."}


def router(storage: Storage) -> APIRouter:
    routes = APIRouter(prefix="/api/admin/albums")

    @routes.post("")
    async def create(request: Request) -> dict:
        # Parsing limits also cap multipart part counts and text field sizes.
        async with request.form(max_files=MAX_FILES, max_fields=2, max_part_size=1024) as form:
            uploads = form.getlist("photos")
            title, request_id = form.get("title"), form.get("request_id")
            if not isinstance(title, str) or not isinstance(request_id, str) or any(not isinstance(f, UploadFile) for f in uploads):
                raise HTTPException(422, "Supply a title, request ID, and JPEG photos.")
            try:
                return await run_in_threadpool(create_album, storage, title, request_id, uploads)
            except (OSError, sqlite3.Error):
                logger.exception("Album creation storage failure")
                raise HTTPException(503, "Could not save album. Retry with the same selection.") from None

    @routes.put("/order")
    def reorder(order: AlbumOrder) -> dict:
        with connect(storage) as db:
            db.execute("BEGIN IMMEDIATE")
            current = [row[0] for row in db.execute("SELECT id FROM albums WHERE published = 1 ORDER BY position, id")]
            if len(order.ids) != len(set(order.ids)) or set(order.ids) != set(current):
                raise HTTPException(409, "Album list changed. Reload before moving albums.")
            if current != order.ids and current != order.previous:
                raise HTTPException(409, "Album order changed. Reload before moving albums.")
            db.executemany("UPDATE albums SET position = ? WHERE id = ?", enumerate(order.ids))
        return {"ids": order.ids}

    @routes.delete("/{album_id}")
    def delete(album_id: str) -> dict:
        return delete_album(storage, album_id)

    return routes
