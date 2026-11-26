# Photo Gallery

A photography portfolio built with React, TypeScript, and Vite on the frontend, and FastAPI on the backend.

The homepage is a local frontend album gallery with three sample series and a fullscreen viewer. The sample albums API remains separate; API integration, uploads, CMS, and persistent storage are not implemented. Only the Vite frontend server is needed.

## Album gallery demo

The black portfolio retains three columns on desktop, two at 1000px and below, and one at 600px and below. Each nonempty album has one cropped 3:2 cover without a visible title beneath it; its button retains an accessible album name. Album order comes from `frontend/src/data/albums.ts` and `sample-albums.json`; the first ordered photo is always the cover. Every opening, including reopening, starts at photo 1.

Click, Enter, or Space opens a cover. Previous/Next and Left/Right wrap only within that album; one-photo albums disable Previous/Next. The viewer shows the album title, photo count, and complete uncropped image. Up to five distinct nearby thumbnails select photos, with the current photo marked. The strip is vertical on the right and horizontal below the image at 600px and below. Close or Escape dismisses the dialog, restores cover focus and scrolling. Tab cycles within the dialog; arrow navigation from a thumbnail moves focus to the newly selected thumbnail.

Cover previews reserve space, with the first three eager and later covers lazy. Only the open viewer renders its selected large image and nearby thumbnails; there is no adjacent full-size preloading. Each image has a loading state and readable failure fallback. Broken covers and thumbnails remain buttons; a failed large image does not prevent navigation. Empty albums are omitted; an all-empty collection shows an empty state. No animations or new dependencies were added.

To change the local collection, edit the ordered albums and photos in the sample JSON, using descriptive alt text and actual dimensions for each variant. Reordering the first photo changes both cover and opening image. Static assets are public, with no drafts or private media handling. Data, images, scripts, and feature plans remain Git-ignored by the existing rules and may be absent in a fresh clone; provide these local artifacts before building. Existing samples require no original-source-drive access.

See [the album gallery plan](plans/album-gallery-plan.md) for scope and outstanding browser checks; it supersedes the old flat-gallery handover.

## Prepared album samples

The UI uses 15 sample photos grouped into Mountains & Snow (6), Lakeside Walks (5), and City Visits (4). These are illustrative samples, not verified geographic series or claims about the owner's work.

Images live under `frontend/public/photos/albums/<album-id>/`. Each photo has three JPEG variants, preserving its full proportions without upscaling:

| Variant | Maximum long edge | Intended use |
| --- | --- | --- |
| `thumbnail` | 240px | Nearby viewer thumbnails |
| `preview` | 960px | Homepage album cover |
| `viewer` | 1920px | Fullscreen photograph |

Each variant includes its URL and actual dimensions in the data. The homepage renders only cover previews; opening an album renders its selected viewer image and nearby thumbnails. Importing the metadata does not initiate image downloads. All files in `public` are public assets, including currently unused samples.

The source selection and descriptive alternative text are recorded in `scripts/sample-album-sources.json`. Regenerate on Windows using the original photos folder:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/prepare-sample-albums.ps1 -SourceDirectory 'E:\Danilo\My Pictures\photos'
```

This uses built-in System.Drawing, normalizes EXIF orientation, and creates fresh JPEGs without source EXIF/GPS metadata. Original files are untouched. It overwrites the selected generated variants and JSON; edit the source manifest before regenerating to preserve intentional ordering or alt-text changes. No runtime dependency is added. The 45 generated files total approximately 8 MiB; all 15 thumbnails together are approximately 165 KiB.

Verification (2026-11-26): lint and production build passed; all 45 JPEG paths, dimensions, size limits, and byte-for-byte copies in build output passed checks. Server-render checks confirmed three ordered cover previews with no viewer mounted, and no-album, all-empty, mixed-empty, one-photo, and two-photo grid cases using in-memory fixtures. Browser automation failed to connect to its native pipe. Interactive navigation, focus/scroll behavior, responsive appearance, browser console, throttled/cache-disabled requests, rapid navigation, and broken-image recovery still require browser verification. Server rendering does not verify those behaviors.

## Project structure

```text
frontend/                 React application
  src/App.tsx             Homepage component
  src/index.css           Global styles
  public/                 Public assets
  package.json            Frontend dependencies and commands
  package-lock.json       Locked frontend dependency versions
backend/
  app/main.py             FastAPI application and endpoints
  requirements.txt        Pinned Python dependencies
.gitignore                Ignore rules for local and generated files
AGENTS.md                 Project guidance for Codex
docs/PLAN.md              Scope, decisions, milestones, and progress
```

## Working with Codex

Open the repository root in VS Code so both the frontend and backend are available. [AGENTS.md](AGENTS.md) defines coding conventions, including simple, clean code, and verification expectations. [The implementation plan](docs/PLAN.md) tracks scope, open decisions, and milestones.

Continue with one focused task after reviewing current progress:

> Read AGENTS.md, README.md, docs/PLAN.md, and plans/album-gallery-plan.md. Complete the remaining browser acceptance checks for the album gallery and record the results before starting another milestone.

Review the changes and create a Git checkpoint after each working milestone.

## Prerequisites

- Node.js 24 LTS with npm, or a compatible newer LTS release.
- Python 3.12 for the backend.
- Git and VS Code.

The commands below use Windows PowerShell and start from the repository root. Install the Python extension in VS Code for backend development. The official Codex extension by OpenAI can be used for coding assistance.

## Frontend setup

```powershell
cd frontend
npm.cmd ci
npm.cmd run dev
```

Open the URL printed by Vite, usually http://localhost:5173. Keep the terminal running while developing; saved changes update in the browser. Press Ctrl+C to stop the server.

`npm.cmd ci` installs the versions recorded in `package-lock.json`. When intentionally adding or updating dependencies, use `npm.cmd install` and commit both dependency files.

## Backend setup

Open a second terminal at the repository root:

```powershell
cd backend
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\fastapi.exe dev app/main.py
```

These commands call the virtual environment directly, so PowerShell activation is not required. In VS Code, select `backend/.venv/Scripts/python.exe` through **Python: Select Interpreter**.

The development server reloads when Python files change. Press Ctrl+C to stop it.

| URL | Purpose |
| --- | --- |
| http://127.0.0.1:8000/api/health | Health check returning `{"status":"ok"}` |
| http://127.0.0.1:8000/api/albums | One sample album with an empty photo list |
| http://127.0.0.1:8000/docs | Interactive API documentation |

For later sessions, run `npm.cmd run dev` from `frontend` and `.\.venv\Scripts\fastapi.exe dev app/main.py` from `backend` in separate terminals. Installation is only needed initially or when dependencies change.

## Checks and production build

From `frontend`:

```powershell
npm.cmd run lint
npm.cmd run build
npm.cmd run preview
```

The build checks TypeScript and writes production assets to `frontend/dist`. Preview serves that build locally; it is not a production hosting setup.

From `backend`, check installed dependency compatibility:

```powershell
.\.venv\Scripts\python.exe -m pip check
```

## Connecting the frontend and backend

The Vite API proxy is not configured yet. Before fetching `/api/albums` from React, configure Vite to forward `/api` requests to `http://127.0.0.1:8000`. Production API routing must be configured separately when deploying.

## Version control

Commit source code, configuration, `frontend/package-lock.json`, and `backend/requirements.txt`. Dependencies, virtual environments, build output, caches, logs, and local `.env` files are ignored. Use `.env.example` for documented example settings without secrets.

Header update (2026-11-25): the portfolio header and browser title now use Mihajlo Mandušić. Right-aligned contact links open the supplied Instagram profile and a new email to mixoidm@gmail.com; links wrap on small screens and include visible keyboard focus. Frontend lint/build passed; browser rendering remains unverified.
