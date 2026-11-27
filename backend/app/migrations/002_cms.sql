CREATE TABLE creations (
    request_id TEXT PRIMARY KEY,
    fingerprint TEXT NOT NULL,
    album_id TEXT NOT NULL
);
CREATE TABLE media_cleanup (
    album_id TEXT NOT NULL,
    path TEXT NOT NULL UNIQUE,
    PRIMARY KEY(album_id, path)
);
