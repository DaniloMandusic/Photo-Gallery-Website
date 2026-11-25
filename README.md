# Photo Gallery

A photography portfolio built with React, TypeScript, and Vite on the frontend, and FastAPI on the backend.

The homepage is a local frontend gallery demo with eight photographs, a responsive grid, and a fullscreen viewer. The sample albums API remains separate; API integration, uploads, CMS, and persistent storage are not implemented.

Demo photos live in `frontend/public/photos/`; their display and navigation order comes from `frontend/src/data/photos.ts`. See [the demo plan](plans/frontend-gallery-demo.md) for behavior and verification. Only the Vite frontend server is needed for this demo.

## Gallery demo

The black portfolio uses two generous columns, switching to one at 600px and below. Every gallery frame is 3:2 landscape; images fit inside without cropping or distortion, with dark space around other aspect ratios. Horizontal demo photos lead the ordered collection. The fullscreen viewer shows the complete image. Open a photo with a click, Enter, or Space. The fullscreen viewer provides Previous/Next buttons and Left/Right arrow navigation, wrapping at either end. Close with Escape or Close. The dialog contains keyboard focus, returns focus to the selected photo, and locks/restores background scrolling.

Fixed 3:2 frames reserve space while loading; the first two images load eagerly and later images load lazily. Failed images show a readable fallback in both the grid and viewer. An empty array displays an empty-gallery message. No animation is used, including for users who prefer reduced motion.

To add a demo photo, copy a JPEG into `frontend/public/photos/` and add its `/photos/filename.jpg` URL, descriptive alt text, and actual width/height to the typed array. Reorder array entries to change gallery order. These static assets are public: this demo has no drafts or private media handling.

Verification (2026-11-25): frontend lint and production build passed. All eight build-output JPEGs match the supplied files. Browser automation was unavailable (native pipe connection failed), so desktop/mobile rendering, keyboard/focus/scroll behavior, and interactive loading/failure/empty-state checks still need manual verification.

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

> Read AGENTS.md, README.md, docs/PLAN.md, and plans/frontend-gallery-demo.md. Complete the remaining manual browser checks for the gallery demo and record the results before starting another milestone.

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
