# Photo Gallery

A photography portfolio built with React, TypeScript, and Vite on the frontend, and FastAPI on the backend.

The project currently contains a placeholder homepage and a sample albums API. The photo grid, image viewer, uploads, and persistent storage have not been implemented yet. The frontend is not yet connected to the API.

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

Start with one focused task, for example:

> Read AGENTS.md, README.md, and docs/PLAN.md. Implement milestone 1: connect React to the sample albums API through a Vite proxy, with loading, empty, and error states. Run the relevant checks and update the plan with the result.

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
