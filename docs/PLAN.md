# Photo Gallery implementation plan

## Product goal

A photography portfolio with an owner-only CMS. The owner should be able to open an album, drop in photos, reorder them if needed, and publish without editing code.

## Current status

- Complete: React/TypeScript/Vite scaffold and placeholder homepage.
- Complete: FastAPI health endpoint; SQLite-backed published album and guarded media endpoints replace the sample endpoint.
- Complete: dependency files, Git ignore rules, setup documentation, and project guidance.
- Implemented: local frontend album gallery with three sample series (15 photos), first-photo covers, album-local fullscreen navigation, up to five nearby thumbnails, responsive grid/strip, and image loading/failure/empty states.
- Implemented: frontend API connection, local SQLite metadata, persistent backend-managed JPEGs, versioned schema initialization, one-time sample importer, read-only published-content filtering, and gallery loading/error/Retry states.
- Not implemented: authentication, uploads, CMS, site settings, or production hosting/routing.
- Current milestone: local storage/API implementation complete; browser acceptance remains pending because both browser helpers failed to connect to their native pipe. See [the local storage/API plan](../plans/local-storage-api-plan.md). Broader CMS/launch milestones remain incomplete.

## MVP scope

Public website:
- Responsive portfolio with album/project galleries and a keyboard-accessible fullscreen image viewer.
- About and contact information.
- Published content only.

Owner CMS:
- One owner account with login and logout.
- Create and edit albums and reorder albums and photos. The first photo is always the cover.
- Upload multiple photos with progress and understandable, retryable failures.
- Edit captions and alternative text.
- Preview drafts, publish, unpublish, and confirm deletions.
- Edit basic site details and contact links.

Postponed: multiple owner roles, visitor accounts, comments, payments, client proofing, and video hosting.

## Decisions and open questions

Confirmed:
- React, TypeScript, Vite, plain CSS, and FastAPI in one repository.
- Store image files separately from database metadata.
- Protect editing operations and draft media on the backend.
- Local storage decision (2026-11-27): SQLite via Python's standard library stores metadata; ordinary files under `backend/storage/media` store JPEG variants. Numbered SQL migrations use `PRAGMA user_version`. Environment variables can override the persistent local database/media paths. This supersedes frontend JSON and public album image storage; both servers are now required.
- Local content maintenance is manual database/file editing. No HTTP writes, authentication, CMS, uploads, cloud, or hosting are included in this milestone. Initial sample import is explicit and never resets content on startup or rerun.
- Album browsing decision (2026-11-26): show one cover per series on the homepage. The first ordered photo is the cover and the opening image; viewer navigation stays within that album. Nearby thumbnails appear vertically on desktop and horizontally at 600px and below. This is implemented for static samples; browser acceptance remains pending.

Proposed starting point:
- The local demo opens directly to album covers and a series viewer. Production content and routing remain future scope.
- An owner-only /admin area in the existing frontend.

Still to decide:
- Production persistence/backup operations beyond the chosen local SQLite and numbered SQL migrations.
- Owner authentication, initial account setup, and recovery approach.
- Future hosted image storage, upload formats/limits, and processing; current local storage serves existing JPEG variants only.
- Hosting, production API routing, and backup/restore strategy.
- Search indexing and per-album social-sharing previews, including whether prerendering or server rendering is needed.

Record decisions here as they are made; do not treat proposals as implemented features.

## Milestones and acceptance criteria

### 1. Connect frontend and backend

Implemented 2026-11-27; live proxy and frontend lint/build verified. Interactive browser acceptance remains pending.

- Configure Vite to forward /api requests to FastAPI in development.
- Display the published persisted albums from /api/albums in React.
- Handle loading, success, empty, and error states, with retry on failure.
- Verify the connection in the browser and pass frontend lint/build checks.

### 2. Define content and persistence

Local album/photo/variant persistence implemented 2026-11-27. Site settings, additional descriptive fields, and production operations remain future work; this broader milestone is not fully complete.

- Choose database and migration tooling, and document the decisions.
- Model albums (title, slug, description, order, publication status), photos (storage reference, dimensions, alt text, caption, order, album), and site settings. Derive the cover from the first ordered photo.
- Add migrations and meaningful API tests.
- Ensure data survives a backend restart and public endpoints exclude drafts.
- Keep write operations protected or unavailable publicly until owner authentication is implemented.

### 3. Owner access and initial CMS

- Choose and implement authentication, account setup, and recovery.
- Provide login, logout, and an owner-only admin area.
- Allow the owner to create and edit draft albums.
- Test that unauthenticated requests cannot modify content or retrieve drafts.

### 4. Upload and publish one complete album

- Choose image storage and implement validated multi-photo uploads.
- Generate appropriately sized display images and thumbnails.
- Show upload progress and allow failed uploads to be retried without duplicate successful uploads.
- Add photo ordering and publication controls; moving a photo first sets the cover.
- Verify that the owner can sign in, create an album, upload three photos, and publish it to a basic public album page.
- Verify that drafts remain private, including requests to image URLs.

### 5. Complete CMS editing

- Add album ordering, photo captions/alt text, draft preview, unpublishing, and confirmed deletion.
- Add editing for basic site information and contact links.
- Ensure edits and ordering persist after refresh.
- Ensure unpublishing also removes public access to associated media according to the chosen storage/cache design.

### 6. Build and polish the public gallery

- Confirm wireframes, then build the homepage, album pages, and about/contact content.
- Add a fullscreen viewer with keyboard navigation and appropriate focus handling.
- Use responsive image sizes, reserved image dimensions, and lazy loading where appropriate.
- Check mobile layouts, accessibility, and loading/empty/error states with real photos.

### 7. Prepare for launch

- Configure hosting, HTTPS, production API routing, and persistent image storage.
- Implement the agreed search/social-preview approach.
- Verify authentication, upload limits, and draft privacy in production configuration.
- Check mobile performance and the complete owner workflow.
- Back up both the database and images, and demonstrate a restore.
- Verify content survives deployment and document operation/recovery steps.

## Progress updates

### 2026-11-27 - Fixed Windows media permissions

Investigated live media 404s: the importer had staged files in an owner-only TemporaryDirectory, and renamed album files retained ACLs readable by the importing sandbox account but inaccessible to the user's backend account. Restored inherited permissions only on the imported albums directory and its children. Changed staging to an ordinary uniquely named directory inheriting the configured media root's permissions, preserving copy/hash checks and cleanup. Added a Windows ACL regression test. Backend verification: 13 tests passed, one existing symlink test skipped; all 45 media requests returned HTTP 200 from the user's running FastAPI server and Vite proxy. No frontend changes or content reimport were needed.

### 2026-11-27 - Local storage and read-only gallery API

Implemented SQLite albums/photos/variants with explicit order, publication state, foreign keys, versioned SQL migrations, and configurable persistent paths. Imported the existing 3 albums, 15 photos, and 45 JPEG variants with byte-for-byte verification, then removed only the verified frontend copies. Retained ignored JSON as historical import input. Runtime types, migrations, importer, and tests are in source locations that are not ignored.

React now fetches FastAPI albums with abort-safe loading, empty, failure, and Retry states. Development and preview proxy `/api`, including media. Gallery/viewer CSS and navigation code remain unchanged. Public reads exclude unpublished albums, and media routes require a referenced variant of a published album with safe path resolution; no blanket static mount or HTTP writes exist. Fresh requests use no-store caching. Content changes need a page reload, not a frontend rebuild.

Verification: 9 backend tests passed and one OS symlink-creation test skipped. Covered import reruns/failures, migrations, constraints, ordering/dimensions, exact media bytes, published filtering, missing files, traversal, read-only behavior, backend errors, and persistence/manual title/order/media changes across fresh application instances. Frontend lint/build and pip compatibility passed. All 45 real JPEG dimensions and pre-removal SHA-256 hashes matched. Live Vite proxy returned all 3 albums and 45 JPEGs; rebuilt output contains no migrated album images.

Both browser automation entry points failed with an unavailable native pipe. Desktop/phone appearance, interactive viewer/keyboard/focus/scroll behavior, request timing/cache-disabled loading patterns, delayed gallery loading, downtime/Retry, and missing-image recovery remain browser acceptance work. See README for actual commands and maintenance/backup guidance. Authentication, uploads, CMS, hosting, site settings, and launch remain unimplemented.

### 2026-11-26 - Album sample data prepared

Prepared three static sample albums (15 photos) with 240px thumbnails, 960px previews, and 1920px viewer JPEGs (maximum long edges, no upscaling). Source images remain untouched. Generated variants normalize orientation and omit source metadata. Typed album data records IDs, alt text, ordered photos, and each variant's URL and dimensions. A reproducible Windows script and source selection manifest live in `scripts/`.

This preparation preceded the album gallery implementation recorded below. The UI now consumes these albums; browser acceptance checks remain outstanding. Verification: 45 image files checked for references, dimensions, limits, and orientation metadata; thumbnail contact sheet inspected; frontend lint/build passed. See README.md for regeneration and loading guidance.

When a milestone is completed, update its status and record verification results and any unresolved limitations here. Keep README.md aligned with the actual setup and available commands.

### 2026-11-25 — Local frontend gallery demo

Implemented the ordered typed photo array, proportion-preserving three/two/one-column grid, compact neutral header, and fullscreen viewer. The viewer uses a native modal dialog, explicit Tab cycling, Left/Right navigation with wrapping, Escape/Close, focus return, and background scroll restoration. Images reserve intrinsic space, load eagerly for the first three entries and lazily thereafter, and provide load-error text. An empty array has a dedicated message. No animations or dependencies were added; the backend remains unchanged.

Verification: `npm.cmd run lint` and `npm.cmd run build` passed after correcting a source encoding issue. All eight packaged JPEGs match the supplied assets. Browser access failed because the computer-use native pipe is unavailable. Desktop/375px mobile rendering, touch, keyboard/focus/scroll behavior, and runtime empty/broken-image/loading checks remain unverified. API milestone 1 remains deferred; this demo does not complete the production gallery milestone 6.

### 2026-11-25 - Landscape portfolio refinement

Per user direction, the local demo now uses a black background, light typography, two columns (one on phones), and consistent 3:2 landscape frames. Images fit without cropping or distortion. Existing horizontal photos lead the static array. Fullscreen viewing retains original proportions. Lint/build passed; browser rendering remains unverified. This supersedes the initial white, variable-height grid design.

Header update (2026-11-25): the portfolio header and browser title now use Mihajlo Mandušić. Right-aligned contact links open the supplied Instagram profile and a new email to mixoidm@gmail.com; links wrap on small screens and include visible keyboard focus. Frontend lint/build passed; browser rendering remains unverified.

### 2026-11-26 - Filled gallery tiles

Gallery previews now use centered cover cropping to fill the existing 3:2 landscape tiles without empty borders. This supersedes the previous contained-thumbnail treatment. Fullscreen images remain contained and uncropped; original image files are unchanged. Frontend lint/build passed; visual browser verification was not performed.

Header alignment (2026-11-26): centered the name independently of the right-aligned contact links. On phones, the centered name occupies its own row above the links. Lint/build passed; browser rendering not verified.

Header typography (2026-11-26): enlarged the centered name to a responsive 32-56px size with a modern system sans-serif stack, semibold weight, and tighter letter spacing. No font download is required. Lint/build passed; visual browser verification remains pending.

Header typography refinement (2026-11-26): replaced the semibold sans-serif name with a regular-weight Baskerville/Palatino serif stack and more relaxed letter spacing for a lighter, editorial appearance. Responsive size and centering are retained. Uses installed fonts with Georgia fallback. Lint/build passed; visual browser verification remains pending.

Contact icons (2026-11-26): replaced Instagram and Mail text with lightweight inline SVG icons. Existing destinations are retained, including the mailto link. Links have accessible names, hover titles, visible keyboard focus, and 44px click targets. No dependencies added. Lint/build passed; browser appearance not verified.

Gallery columns (2026-11-26): restored three photos per row on desktop, with two columns at 1000px and below and one at 600px and below. The first three images load eagerly. Cropped 3:2 tiles are retained. Lint/build passed; browser rendering not verified.

### 2026-11-26 - Album cover gallery and series viewer

Implemented the local frontend milestone: nonempty album covers in array order, first-photo opening on every visit, album-local wrapping controls/arrow keys, and up to five distinct nearby thumbnail buttons with a current marker. The thumbnail window clamps near the ends; keyboard navigation from a thumbnail restores focus to the selected thumbnail. Single-photo navigation is disabled. Covers use preview variants, the selected photograph uses its viewer variant, and the strip uses thumbnails. No adjacent full-size preloading, backend changes, dependencies, asset regeneration, or ignore-rule changes were introduced.

Verification: frontend lint/build and diff whitespace checks passed. All 45 JPEG references, dimensions, size limits, and production copies were checked. Server-render assertions passed for ordered cover-only markup, no mounted viewer on the homepage, no albums, all-empty albums, mixed empty/nonempty albums, and one-/two-photo album covers. Fixtures were changed only in memory. Browser automation failed with a native-pipe connection error, so interaction, focus/scroll, desktop/tablet/375px/short-landscape appearance, throttled/cache-disabled network behavior, rapid navigation, browser console, and invalid-image recovery remain unverified. See the feature plan for the full browser checklist. This does not complete the production public gallery or CMS.

Additional restart verification (2026-11-27): after stopping and starting the actual backend process, all album metadata/order matched the import input and all 45 HTTP image responses matched persistent files byte-for-byte through Vite. Documentation local links resolve. The obsolete ignored frontend/src/data/albums.ts module was removed, and lint/build passed again without it. Temporary verification servers were stopped.

Type validation refinement (2026-11-27): added backend parameter/return annotations and replaced importer manual type checks with strict Pydantic sample models. Duplicate IDs and filesystem checks remain explicit. Python annotations alone do not enforce runtime types. Verified 12 backend tests passed, with the existing Windows symlink test skipped; new cases cover wrong types, missing fields, empty collections, invalid dimensions, and duplicate IDs. No frontend or storage migration changes were needed.
