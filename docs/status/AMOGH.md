# Amogh status

Status: M1 in progress (2026-11-13). Code scaffolding done and tested against
synthetic data only. **Live Canvas access is not yet validated.**

## Completed

- Branch `amoghs-branch` pushed to origin.
- Canvas config loader with wrapped secrets and single-user token binding.
- Read-only Canvas client: GET only, pinned to institution origin, Link-header
  pagination, 401/403/404 mapping, bounded retry on throttling/5xx.
- `validate_access` script for the own-account token path.
- Upload fallback: validated, hashed, course-labeled private local storage
  producing SourceDocument records marked `provenance.mode = upload, demo = true`.
- `.env.example` with placeholders; real values go in gitignored
  `services/api/.env.canvas.local`.

## Commands and verification

Run from `services/api`:

- `python3 -m unittest app.modules.canvas.tests.test_m1` → 18 tests pass
  (Python 3.14.3). All synthetic; a fake transport stands in for Canvas.
- `python3 -m app.modules.canvas.validate_access` → exits 2 with
  "CANVAS_BASE_URL is not set" (expected; nothing configured yet).
- Not run: any request to a real Canvas instance; `upload_local` on real files.

## Interfaces and fixtures delivered

- See [canvas module README](../../services/api/app/modules/canvas/README.md).
- Optional `provenance` object added to upload SourceDocument records
  (additive; to be written into contracts/academics.md with M2 schemas).
- No fixtures yet (M2–M4).

## Dependencies and blockers

- External: institution Canvas base URL — to be confirmed by Amogh.
- External: whether the school issues OAuth developer keys to students —
  unknown; assume unavailable until confirmed. OAuth flow not built.
- External: whether the school allows personal access token creation — unknown.
- Request to Agastya: initialize the Python manifest/FastAPI core so the canvas
  router can be registered; an HTTP client dependency (e.g. httpx) for M2
  concurrent ingestion; shared jobs table handler contract; private storage
  bucket to replace the local `.local/academics` stand-in.
- Request to Adi: current-user shape / test app user ID to bind the demo token to.

## Next actions

- Fill in `.env.canvas.local`, run `validate_access`, record the result here.
- If token creation is blocked, demonstrate upload mode and record the blocker.
- Then M2: inventory modules, pages, files, assignments, calendar events.
