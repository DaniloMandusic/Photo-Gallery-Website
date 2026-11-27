# Photo Gallery

A local photography portfolio using React, TypeScript, Vite, plain CSS, FastAPI, SQLite, and backend-managed JPEG files. Both local servers are required. A minimal local album CMS is available at `/admin`. Authentication and hosting remain deferred: the page and write endpoints are **unauthenticated**, for local development only.

## Run locally

Prerequisites: Node.js 24 LTS (or compatible newer LTS), Python 3.12, Git. Commands use PowerShell from the repository root.

```powershell
# Initial dependency installation
npm.cmd ci --prefix frontend
py -3.12 -m venv backend/.venv
& backend/.venv/Scripts/python.exe -m pip install -r backend/requirements.txt

# Optional explicit schema initialization; startup also applies migrations
& backend/.venv/Scripts/python.exe -m backend.app.storage

# Terminal 1: backend
& backend/.venv/Scripts/python.exe -m uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000

# Terminal 2: frontend
cd frontend
npm.cmd run dev
```

Open the URL Vite prints (normally http://localhost:5173). Development and `npm.cmd run preview` proxy `/api`, including images, to `http://127.0.0.1:8000`. Production hosting/routing is not configured. No CORS configuration is needed for this local same-origin proxy.

| Backend URL | Purpose |
| --- | --- |
| `/api/health` | `{"status":"ok"}` |
| `/api/albums` | Ordered published albums and photo metadata; empty collection returns `[]` |
| `/api/media/{photo_id}/{thumbnail,preview,viewer}` | Referenced JPEG of a published album |
| `/docs` | API documentation |

Public `/api/albums` and media routes remain read-only. Backend failures produce unsuccessful responses rather than empty collections. React displays loading, empty, and retryable error states without falling back to sample JSON. Keep servers bound to loopback; this milestone does not provide protected owner access or production deployment.

## Minimal local CMS

Open `/admin` on the Vite URL. Add album opens a title and multi-photo form. Move earlier/later sets the photo order before creation. The first photo is the cropped 3:2 cover and opening image. Choose photos again replaces the selection. Create album prepares every photo and immediately appends the complete album to the gallery. There are no saved drafts or separate publication controls.

Stored albums have only Move up, Move down, and Delete controls. Moves save immediately; boundary buttons are disabled. Delete asks for confirmation with the title and photo count. Cancel changes nothing. Existing titles, photos, and photo order cannot be edited: delete and recreate to change them. View gallery performs a fresh visit; already-open tabs retain their fetched snapshot until refreshed.

Upload limits: **JPEG content only; 1–30 photos; 20 MiB per photo; 100 MiB combined; 40 million decoded pixels per photo; trimmed title 1–120 characters**. The incoming multipart request is capped at 101 MiB including overhead, even without Content-Length. Pillow decodes images, normalizes orientation, strips metadata, and writes 240/960/1920px maximum-long-edge variants without upscaling. Storage IDs are generated independently of filenames. New alt text uses album title and photo number, not filenames; these fallbacks do not describe image contents. Original uploads on the owner's computer are untouched.

The form shows upload/processing status and disables conflicting controls. Validation failures retain the selection. An uncertain network/server result locks the selection and offers Retry same creation. Durable request IDs and content fingerprints prevent ordinary/concurrent retries from creating duplicates. Keep the page open until confirmed: reloading loses the local form/request ID, so check the saved list before creating again. Upload resuming and percentage progress are not implemented.

| Write endpoint | Contract |
| --- | --- |
| `POST /api/admin/albums` | Multipart `title`, UUID `request_id`, repeated `photos` in intended order; returns album `id` |
| `PUT /api/admin/albums/order` | JSON `ids` and `previous` arrays of all published album IDs; rejects missing, duplicate, unknown, or stale ordering |
| `DELETE /api/admin/albums/{album_id}` | Repeatable deletion/cleanup; returns `deleted`, `cleanup_pending`, and `message` |

All variants are staged privately before album metadata and the creation receipt commit together. Ordinary failures roll back and clean up prepared files. SQLite and the filesystem cannot share a transaction: a crash between rename and commit, or a cleanup failure, can leave private orphans. Stop the backend and compare files with database references before removing orphans manually; never remove a populated media directory to retry creation.

Deletion first commits metadata removal and a durable `media_cleanup` queue, revoking public access. It then removes recorded JPEG paths, protecting files still referenced elsewhere. Locked/unsafe files produce an explicit warning and Retry deletion / file cleanup button. Pending paths survive restarts. After a page reload, inspect `media_cleanup` and retry DELETE with its album ID once the filesystem issue is resolved. A warning means the album is removed but some private files remain. There is no trash/undo.

## Persistent local storage

Defaults are resolved relative to the backend source, independent of the working directory:

- `backend/storage/gallery.sqlite3`: metadata, ordering, publication state, schema version, and initial-import marker.
- `backend/storage/media/`: image files; imported samples are under `albums/<album-id>/`.

These paths survive backend restarts and frontend builds and are Git-ignored. Optional `GALLERY_DATABASE` and `GALLERY_MEDIA_ROOT` environment variables override them; use absolute paths and set the same values in the importer and backend terminals. Relative overrides resolve against the process working directory. Environment variables are read directly; `.env` files are not automatically loaded by the application.

SQLite uses Python's standard library, foreign keys, transactional numbered SQL migrations in `backend/app/migrations/`, and `PRAGMA user_version`. Startup applies pending migrations without seeding or resetting content. A newer unsupported database version fails startup.

Media routes look up photo/variant records and their album publication status on every request. They reject missing records/files and unsafe paths, including resolved paths outside the media root. No directory or static storage mount exists. Album and successful media responses use `Cache-Control: no-store`, so fresh reads reflect changes and unpublishing. Already downloaded/displayed bytes cannot be revoked. CMS operations write storage through the backend; direct maintenance remains a trusted local operation.

## Initial sample import

The original collection contains Mountains & Snow (6 photos), Lakeside Walks (5), and City Visits (4). Each photo has thumbnail, preview, and viewer JPEG variants, with maximum long edges of 240, 960, and 1920 pixels (no upscaling). These are illustrative samples, not verified geographic series or claims about the owner's work.

For an **unimported** local collection with the original JSON and prepared files available:

```powershell
& backend/.venv/Scripts/python.exe -m backend.app.import_samples --metadata frontend/src/data/sample-albums.json --source-public frontend/public
```

The command validates JSON with strict typed Pydantic models (already installed with FastAPI), reporting field-specific errors without coercing invalid types. It also checks duplicate IDs, expected source paths, and JPEG inputs, stages and hash-checks copies, then inserts metadata in one transaction. Samples are imported as published. It requires an empty collection and refuses an existing destination `media/albums` directory. Missing inputs/copy failures do not commit a partial collection. A crash or commit failure after the directory rename can leave an orphan `media/albums`; inspect and move that directory aside before retrying against an empty database. Never remove a populated collection to force an import.

A successful import records a durable marker. Every later run reports already imported and leaves all data/files unchanged, even if source inputs are gone. It is not a synchronization, repair, or content-update tool.

This workspace has already imported all 3 albums, 15 photos, and 45 variants. After verifying source/destination SHA-256 hashes, the 45 frontend copies were removed. The JSON remains an ignored historical import input; neither it nor `frontend/src/data/albums.ts` is a runtime dependency. All required frontend types, importer, migrations, and tests live in tracked source locations.

The existing ignore rules also exclude sample inputs, scripts, and feature plans. A fresh clone starts with an empty gallery unless supplied with a database/media backup or the original import inputs. Do not regenerate images for ordinary startup or rerun the legacy preparation script into `frontend/public`: that would reintroduce public static copies. Original source photos were not accessed or changed.

## Manual maintenance and backups

On Windows, imported files inherit the media directory's permissions so the account running FastAPI can read them. The importer uses an ordinary staging directory: Python's owner-only temporary-directory permissions can otherwise survive a rename and cause media 404 responses under a different account. The initial workspace import's permissions were repaired on 2026-11-27; all 45 media URLs then returned HTTP 200 through both the running backend and Vite. A Windows ACL regression test covers future imports.

Stop the backend before file moves, multi-step maintenance, or backups. Back up **both** the SQLite database and entire media directory together outside disposable build output. Restore both together and start the backend with the matching paths. Automated backups and a production restore procedure are future work.

Use a SQLite editor with foreign keys enabled, or Python's built-in `sqlite3`. For example, from the repository root, update an album title/order without rebuilding React:

```powershell
@"
from backend.app.storage import Storage, connect
with connect(Storage.from_environment()) as db:
    db.execute('UPDATE albums SET title = ?, position = ? WHERE id = ?',
               ('Mountains & Snow', 0, 'mountains-and-snow'))
"@ | & backend/.venv/Scripts/python.exe -
```

- `albums`: stable `id`, `title`, nonnegative `position`, `published` (0 or 1; defaults to 0).
- `photos`: globally unique stable `id`, `album_id`, `alt`, nonnegative `position`.
- `variants`: `photo_id`, `role` (`thumbnail`, `preview`, `viewer`), unique relative `path` inside the media root, positive actual `width`/`height`. Supply all three roles for every photo. JPEGs only. Use lowercase hyphenated IDs as in the samples.
- Album and photo ordering is `position`, then `id` for ties. The first ordered photo is always the cover and opening photo. Empty albums are omitted by the frontend.

Use `/admin` for ordinary creation, deletion, and album ordering. For advanced manual maintenance, prepare the three JPEG files outside the frontend, create a draft album and related photo/variant rows in a transaction, verify paths/dimensions, then set `published = 1`. To unpublish, set it to 0. Keep paths relative with forward slashes; do not use symlinks, absolute paths, traversal, or the database file as media. There is no draft/owner-preview UI. Migration 002 adds creation receipts and pending cleanup records without resetting content. Refresh the page after maintenance to fetch updated content; no frontend rebuild is required. The open viewer retains its fetched snapshot until reload.

## Gallery behavior

The existing black portfolio layout is preserved: three columns on desktop, two at 1000px and below, one at 600px and below. Covers are cropped 3:2 previews with accessible album names and no visible titles beneath them. Every opening starts at photo 1.

Click, Enter, or Space opens a cover. Previous/Next and Left/Right wrap within that album; one-photo albums disable navigation. The fullscreen viewer shows the uncropped image, title, count, and up to five nearby thumbnails. Thumbnails are vertical on desktop and horizontal below the image on phones. Close/Escape restores cover focus and scrolling; Tab cycles within the dialog.

Only cover previews are rendered on the homepage, with the first three eager and later covers lazy. Only the open viewer renders its selected large image and nearby thumbnails; no adjacent large-image preloading is added. Per-image loading/failure states remain available, and a failed image does not prevent navigation.

## Checks and current verification

```powershell
# Repository root
& backend/.venv/Scripts/python.exe -m unittest discover -s backend/tests -v
& backend/.venv/Scripts/python.exe -m pip check
git diff --check

# frontend/
npm.cmd run lint
npm.cmd run build
npm.cmd run preview
```

Historical storage-milestone verification (superseded by the CMS checks below): 9 backend tests passed; 1 symlink test skipped because Windows did not permit symlink creation. Tests use disposable storage and cover ordering, byte responses, import reruns/failures, migrations, constraints, draft/media filtering, read-only routes, traversal, missing files, backend failures, and persistence across fresh application connections. A manual title/order edit and replacement media survive migration/import reruns and appear through a fresh API application without rebuilding the frontend. Lint, production build, dependency compatibility, and diff whitespace checks passed.

Real-data checks: exactly 3 albums/15 photos/45 variants imported; all 45 source/destination hashes and actual JPEG dimensions verified; repeat import left content unchanged; all 45 images served successfully through the live Vite/FastAPI proxy; migrated album images absent from frontend public assets and rebuilt output.

Browser automation and its Windows fallback both failed to connect to the native pipe. Desktop/phone visual checks, all-album viewer navigation, keyboard/focus/scroll behavior, reopen-at-first-photo, cache-disabled request patterns, delayed loading, downtime/Retry recovery, and missing-image recovery remain unverified in a browser. Source preservation and HTTP/tests do not substitute for these checks.

See [project guidance](AGENTS.md), [milestone status](docs/PLAN.md), and the local [feature plan](plans/local-storage-api-plan.md). Owner authentication, existing-album editing, AI image generation, cloud services, and hosting are not implemented. See the local [minimal CMS plan](plans/minimal-cms-plan.md) for this milestone.

Additional restart verification (2026-11-27): after stopping and starting the actual backend process, all album metadata/order matched the import input and all 45 HTTP image responses matched persistent files byte-for-byte through Vite. Documentation local links resolve. The obsolete ignored frontend/src/data/albums.ts module was removed, and lint/build passed again without it. Temporary verification servers were stopped.


### 2026-11-27 ? Minimal local CMS verification

Implemented `/admin`, complete immediate JPEG album creation with creation-only photo ordering, confirmed deletion, and immediate album moves. The first photo remains cover/opening image. Public gallery component and styles are unchanged. Authentication and hosting are explicitly deferred; write endpoints are unauthenticated and must remain local. Existing-album editing, saved drafts, publication controls, captions editing, and broader CMS features remain unimplemented.

Checks: 24 backend tests passed, with one existing Windows symlink-permission test skipped (25 total). Coverage includes real JPEG order/dimensions/orientation/metadata removal, count/byte/pixel/body limits including chunked requests, invalid images, processing/rename/transaction/commit failures, concurrent/repeated creation, deleted receipts, stale/invalid ordering, cleanup failures/retry/isolation, draft/staging privacy, and Windows ACL inheritance. One test run hit a transient Windows access-denied error on directory rename; creation returned a recoverable 503 with no published album, and the full rerun passed. This remains a possible retryable filesystem limitation. `pip check`, frontend lint/build, and whitespace checks passed.

Live HTTP verification used a disposable copy of all 3 existing albums / 15 photos / 45 variants through Vite preview on isolated ports. Verified `/admin` serves, ordered three-photo creation appends immediately, duplicate retry returns the same album, moves persist across a confirmed backend process stop/restart, deletion removes only the test album, and old media URLs return 404. All 45 original media responses remained byte-identical. All 46 original storage file hashes were unchanged during the successful isolated run; verification servers were stopped.

Verification incident: an initial readiness check accepted the already-running backend on port 8000. It added and deleted only the generated test album and shifted existing album positions. Removed its creation receipt and restored the existing album positions to 0/1/2; existing photos and variants were retained. Subsequent verification used separate ports, refused occupied ports, checked process liveness, and confirmed the backend was unreachable before restart. The running backend applied additive migration 002; no content reset or reimport occurred.

Interactive browser acceptance remains blocked: both the browser tool and Windows Computer Use fallback returned a missing native-pipe connection error. Desktop/phone layout, selection/reordering controls, confirmation cancellation, keyboard/focus/scroll behavior, viewer navigation and first-photo reopening, and loading/error/retry interactions were not exercised in a browser. HTTP/tests do not substitute for those checks.

Remaining operational limits: crash/failed-cleanup private orphans can require manual inspection; pending deletion cleanup persists in SQLite but must be retried by album ID after a page reload; local creation selections/request IDs do not survive reload; no upload resuming or percentage progress. See README for exact formats/limits and recovery details.
