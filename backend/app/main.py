from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from typing import Literal
from urllib.parse import quote

from fastapi import FastAPI, HTTPException, Response
from fastapi.responses import FileResponse

from .storage import Storage, connect, media_path, migrate


def create_app(storage: Storage | None = None) -> FastAPI:
    storage = storage or Storage.from_environment()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        migrate(storage)
        yield

    app = FastAPI(title="Photo Gallery API", lifespan=lifespan)

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/albums")
    def list_albums(response: Response) -> list[dict[str, object]]:
        response.headers["Cache-Control"] = "no-store"
        with connect(storage) as db:
            # Keep metadata consistent during manual edits.
            db.execute("BEGIN")
            albums = []
            for album in db.execute("SELECT * FROM albums WHERE published = 1 ORDER BY position, id"):
                photos = []
                for photo in db.execute("SELECT * FROM photos WHERE album_id = ? ORDER BY position, id", (album["id"],)):
                    variants = {
                        variant["role"]: {
                            "src": f'/api/media/{quote(photo["id"], safe="")}/{variant["role"]}',
                            "width": variant["width"], "height": variant["height"],
                        }
                        for variant in db.execute("SELECT * FROM variants WHERE photo_id = ?", (photo["id"],))
                    }
                    if len(variants) != 3:
                        raise HTTPException(500, "Incomplete photo metadata")
                    photos.append({"id": photo["id"], "alt": photo["alt"], **variants})
                albums.append({"id": album["id"], "title": album["title"], "photos": photos})
            return albums

    @app.get("/api/media/{photo_id}/{role}")
    def media(photo_id: str, role: Literal["thumbnail", "preview", "viewer"]) -> FileResponse:
        with connect(storage) as db:
            variant = db.execute(
                "SELECT v.path FROM variants v JOIN photos p ON p.id = v.photo_id "
                "JOIN albums a ON a.id = p.album_id "
                "WHERE p.id = ? AND v.role = ? AND a.published = 1", (photo_id, role),
            ).fetchone()
        if variant is None:
            raise HTTPException(404, "Photo not found")
        try:
            path = media_path(storage.media, variant["path"])
        except ValueError:
            raise HTTPException(404, "Photo not found") from None
        if path.suffix.lower() not in (".jpg", ".jpeg") or not path.is_file():
            raise HTTPException(404, "Photo not found")
        return FileResponse(path, media_type="image/jpeg", headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"})

    return app


app = create_app()
