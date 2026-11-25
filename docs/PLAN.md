# Photo Gallery implementation plan

## Product goal

A photography portfolio with an owner-only CMS. The owner should be able to open an album, drop in photos, reorder them if needed, and publish without editing code.

## Current status

- Complete: React/TypeScript/Vite scaffold and placeholder homepage.
- Complete: FastAPI health endpoint and sample albums endpoint.
- Complete: dependency files, Git ignore rules, setup documentation, and project guidance.
- Not implemented: frontend API connection, persistent data, authentication, uploads, CMS, or public gallery.
- Current milestone: connect the frontend to the sample albums API (milestone 1).

## MVP scope

Public website:
- Responsive portfolio with album/project galleries and a keyboard-accessible fullscreen image viewer.
- About and contact information.
- Published content only.

Owner CMS:
- One owner account with login and logout.
- Create and edit albums, select covers, and reorder albums and photos.
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

Proposed starting point:
- An album-cover homepage linking to individual project galleries. Confirm this layout before visual implementation.
- An owner-only /admin area in the existing frontend.

Still to decide:
- Database and migration tooling.
- Owner authentication, initial account setup, and recovery approach.
- Image storage, supported formats, upload limits, and thumbnail processing.
- Hosting, production API routing, and backup/restore strategy.
- Search indexing and per-album social-sharing previews, including whether prerendering or server rendering is needed.

Record decisions here as they are made; do not treat proposals as implemented features.

## Milestones and acceptance criteria

### 1. Connect frontend and backend

- Configure Vite to forward /api requests to FastAPI in development.
- Display the sample album from /api/albums in React.
- Handle loading, success, empty, and error states, with retry on failure.
- Verify the connection in the browser and pass frontend lint/build checks.

### 2. Define content and persistence

- Choose database and migration tooling, and document the decisions.
- Model albums (title, slug, description, cover, order, publication status), photos (storage reference, dimensions, alt text, caption, order, album), and site settings.
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
- Add cover selection, photo ordering, and publication controls.
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

When a milestone is completed, update its status and record verification results and any unresolved limitations here. Keep README.md aligned with the actual setup and available commands.
