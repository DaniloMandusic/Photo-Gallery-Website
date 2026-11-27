CREATE TABLE albums (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    position INTEGER NOT NULL CHECK(position >= 0),
    published INTEGER NOT NULL DEFAULT 0 CHECK(published IN (0, 1))
);
CREATE TABLE photos (
    id TEXT PRIMARY KEY,
    album_id TEXT NOT NULL REFERENCES albums(id) ON DELETE CASCADE,
    alt TEXT NOT NULL,
    position INTEGER NOT NULL CHECK(position >= 0)
);
CREATE INDEX photos_album_order ON photos(album_id, position, id);
CREATE TABLE variants (
    photo_id TEXT NOT NULL REFERENCES photos(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK(role IN ('thumbnail', 'preview', 'viewer')),
    path TEXT NOT NULL UNIQUE,
    width INTEGER NOT NULL CHECK(width > 0),
    height INTEGER NOT NULL CHECK(height > 0),
    PRIMARY KEY(photo_id, role)
);
CREATE TABLE imports (name TEXT PRIMARY KEY);
