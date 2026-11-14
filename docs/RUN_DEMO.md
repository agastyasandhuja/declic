# Run the integrated déclic demo

The app uses Supabase Auth, a private Supabase `lesson-videos` bucket, and MongoDB
Atlas application collections. The API and background workers run on your Mac.
Canvas uses each student's personal access token; institutional OAuth is not needed.

## Configure once

Use Node 24, Python 3.11+, `uv`, Docker, and the pinned dependencies:

```sh
npm ci
cd services/api
uv sync --locked
cd ../..
```

Copy `services/api/.env.example` to `services/api/.env` and
`services/api/.env.gemini.example` to `services/api/.env.gemini.local`.
Existing root `.env` values are also loaded. Set server-only values:

- `MONGODB_URI`, `MONGODB_DATABASE`: the application Atlas database.
- `SUPABASE_URL`, `SUPABASE_PUBLISHABLE_KEY`, `SUPABASE_SERVICE_ROLE_KEY`.
  Existing `SUPABASE_SERVICE_KEY` is accepted as an alias.
- `CONNECTION_ENCRYPTION_KEY`: generate once with the command in the example.
  Keep this stable and private; replacing it invalidates saved provider connections.
- `CANVAS_BASE_URL`: institution origin, default `https://umamherst.instructure.com`.
- `GEMINI_API_KEY` in `.env.gemini.local`; the example selects `gemini-3.5-flash-lite`.
  This is a [stable structured-output model](https://aistudio.google.com/docs/models/gemini-3.5-flash-lite).
  Embeddings use `gemini-embedding-001`.
- `ANTHROPIC_API_KEY`, `VIDEO_CLAUDE_MODEL` (default `claude-sonnet-4-5`),
  `ELEVENLABS_API_KEY`, and the narrator/Peter/Stewie voice IDs.
- `VIDEO_RENDER_IMAGE`: the image built using the renderer's documented Docker
  instructions. Existing local image: `hackumass-renderer:reference-v9-semantic`.

Place the local licensed/demo assets in `.local/video-assets` as described in the
video README. They are intentionally excluded from Git. Run Docker before workers.
Never put server keys, Instagram passwords, or Canvas tokens in `EXPO_PUBLIC_*`.

```sh
python3 scripts/run-demo.py init
python3 scripts/run-demo.py check
```

`init` applies ordered Atlas definitions/indexes. It does not create a Supabase
project or make a bucket public. `check` prints configuration presence, never secrets.
The existing cloud project and private bucket were reachable during integration.

## Start on the Mac

Use separate terminals from the repository root:

```sh
python3 scripts/run-demo.py api --port 8010
python3 scripts/run-demo.py workers
```

Set `VIDEO_GENERATION_ENABLED=false` to pause paid video jobs while keeping the
API, feed and cached videos available. The local demo is currently paused at the
user's request to conserve credits. Set it to `true` and restart workers when ready.
`VIDEO_MAX_CLAUDE_CALLS=6` caps generation/review attempts per video, including
repairs and restarts; failed checks never publish. Model override is explicit.

Workers default to three import/preparation tasks and two concurrent video tasks.
Course inventory and extraction each have bounded concurrency. Jobs survive restarts,
renew leases while working, and retry bounded transient failures. When Gemini is
unconfigured, academic jobs remain queued; Instagram can continue independently.

Copy `apps/mobile/.env.example` to `apps/mobile/.env`. Set only the public Supabase
URL/key and `EXPO_PUBLIC_FEED_SOURCE=api`. For a phone, use a trusted HTTPS API
origin; the authenticated client deliberately rejects plain HTTP. One option is
the Expo HTTPS tunnel with its development proxy:

```sh
HACKUMASS_PREVIEW_API=1 HACKUMASS_API_PORT=8010 npm start --workspace @hackumass/mobile -- --tunnel
```

Leave `EXPO_PUBLIC_API_BASE_URL` empty when using the supported Expo tunnel origin,
or set it to your own HTTPS tunnel forwarding to the API. With a separate browser
origin, set `API_CORS_ORIGINS` to a JSON list containing that exact origin. The
Expo proxy forwards only allowlisted authenticated routes to loopback; it never
forwards cookies. The mobile runtime must support the versions pinned in this repo.

## Student flow

1. Create an account and follow email confirmation if the project requires it.
   Sign in. Native auth sessions use SecureStore and restore on reopening.
2. Open **Courses**. In Canvas, generate a personal access token under
   **Account → Settings → New Access Token**; paste it into the app and save.
   The backend verifies it and stores authenticated encryption bound to your user.
3. Connect Instagram in the same screen. Passwords are used for the login request
   and never persisted. The reusable provider session is encrypted server-side.
   If Instagram asks for a checkpoint, complete it in Instagram and reconnect.
4. Return to **Feed**. Entertainment fills independently. Prepared lessons appear
   as each video becomes ready, followed by questions grounded in the course sources.
   **Courses → Preparing your feed** shows queue/generation state and missing Gemini.
5. Answer a question to continue. An incorrect answer still unlocks the feed and
   changes future ranking toward another explanation. A submission failure keeps
   the answer retryable without double grading; recovery can continue ungraded.

Ten minutes is a testing window, not a completion guarantee. Course count, source
size, provider latency/limits and render time determine how many lessons are ready.
A failed lesson never blocks entertainment. Initial results do not wait for every
course or video to finish.

## Reuse and recommendations

Topics are matched within the same user's compatible subject/level/language/notation
using normalized Gemini embeddings and conservative cosine similarity. Concurrent
requests share canonical generation keys. Course-specific quiz/source attribution
remains separate even when a video is reused. Private coursework is not promoted
into another student's catalog.

The current policy is a deterministic baseline: progressive study density, course
fairness, available inventory, exam urgency, mastery and spacing, with alternate
variants after mistakes. Courses without an eligible upcoming assessment can use
source-backed current-unit suggested practice; this does not imply exam coverage.
It implements the research-informed constraints but is
not a trained or experimentally validated bandit. See the research and task docs
for the separate data collection and evaluation work required before promotion.

Private demo videos pass content, frame, artifact-digest and media checks before
publication; their records explicitly say human review is pending. Shared/public
publication still requires manual approval. Signing happens only after ownership
checks. The renderer has no provider credentials or network egress.

## Verification and remaining live checks

See `docs/status/AGASTYA.md` for commands actually run and the current evidence.
Synthetic tests do not prove a student's Canvas permissions, Instagram checkpoint
behavior, Gemini access, or physical iPhone playback. Keep server `.env` files,
provider sessions, source documents and generated media out of commits.
