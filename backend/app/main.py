from fastapi import FastAPI

app = FastAPI(title="Photo Gallery API")


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/albums")
def list_albums():
    return [
        {
            "id": 1,
            "title": "My First Album",
            "slug": "my-first-album",
            "photos": [],
        }
    ]