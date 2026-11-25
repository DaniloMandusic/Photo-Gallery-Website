# Project guidance

## Product and scope

- Build a photography portfolio with a simple owner-only CMS.
- Make uploading photos, organizing albums, choosing covers, reordering content, and publishing easy for a nontechnical owner.
- Read README.md for setup and docs/PLAN.md for scope, decisions, and the current milestone.
- Implement one focused milestone at a time unless the user requests broader work.
- Distinguish implemented behavior from planned features. Update the plan as milestones are completed.

## Stack

- Frontend: React, TypeScript, Vite, and plain CSS in frontend/.
- Backend: FastAPI and Python in backend/.
- Database, authentication, image storage, and hosting choices are not finalized. Record decisions in docs/PLAN.md when they are made.

## Code quality and working conventions

- Write simple, clean, readable code. Prefer clear names, small focused functions, and straightforward control flow.
- Use the simplest solution that meets the current requirements. Avoid speculative abstractions, unnecessary dependencies, and premature optimization.
- Follow existing patterns; extract shared code when there is a concrete need.
- Use comments to explain non-obvious reasons or constraints, not to repeat the code.
- Preserve unrelated user changes and keep changes scoped to the task.
- Update documentation when setup, commands, or behavior change.

## Product quality

- Make public pages and admin screens responsive and accessible, with keyboard-friendly controls.
- Include loading, empty, and error states for data-driven UI.
- Enforce authorization for CMS operations on the backend, not just in the frontend.
- Keep draft content and its images private.
- Validate uploads on the backend and handle failures clearly.
- Keep secrets out of source code and frontend bundles.

## Verification

- For frontend code changes, run `npm.cmd run lint` and `npm.cmd run build` from frontend/.
- Use `backend/.venv/Scripts/python.exe` for backend Python commands on Windows.
- Add meaningful tests for new backend behavior, especially authentication, uploads, and publishing rules. There is no committed backend test suite yet.
- Run checks appropriate to the change; documentation-only changes need link and content checks rather than application builds.
- Report what was checked and anything not verified.
