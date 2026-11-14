# déclic integration verification — November 14, 2026

## Branch assembly

Worktree: `.local/declic-app`, branch `integration/declic-app`.
Base: `46d6aa8` (local Agastya learning engine + previous Atlas integration).
Merge: `bbb3481`, bringing the outstanding `origin/adi-live-instagram-feed`
(`afbe424`) and `origin/amoghs-branch` (`5f5c3ba`) together. Atlas readiness was
already subsumed by the selected heads. `git branch -r --no-merged HEAD` returned
no branches after the merge, including origin/main and the older Adi app branches.

The original checkout and its uncommitted video/renderer work were preserved.
Those uncommitted experiments are not part of the branch merge.

## Commands and observed results

- `npm install --ignore-scripts`: repaired the pre-existing workspace lock mismatch
  for `@hackumass/mobile-academics`; added pinned matching `expo-font@58.0.12`.
- `npm run typecheck`: passed.
- `npm test --workspace @hackumass/mobile`: 36 tests passed with local loopback
  allowed, including session deduplication, prefetch, ready-buffer reuse, academic
  date precision and malformed profile handling. The initial sandboxed attempt
  failed only because the local proxy test could not bind a socket.
- `npm run contracts:check`: generated types match versioned schemas.
- `npx expo export --platform ios --platform web`: both bundles exported.
- Shared API venv, `pytest services/api/tests services/api/app/modules/curriculum/tests -q`:
  86 passed, 7 skipped for missing real MongoDB test configuration.
- Instagram venv, `python -m unittest discover -s services/api/app/modules/entertainment/tests -v`:
  22 passed, including POST-body pagination and continuation/leftover preservation
  across reloads. These provider/auth responses are synthetic.
- Running those provider tests in the shared core venv instead produced two import
  failures because instagrapi is absent there; this is a dependency integration gap.
- Live `instagram_connection --check` against the already-bound private session:
  two provider pages, six unique Reels, continuation available. No new login,
  private feed metadata, tokens or cookies printed or committed.
- `git diff --check`: passed.

Commands used the available Node 26.12.0. The repo's declared Node 24 version is
still the supported target; npm printed an engine warning. No engine constraint
was changed to hide that difference.

## UI checks actually performed

Browser at 390 × 844: welcome → demo → video feed → next clip; observed the active
HTML video at readyState 4, with playback time advancing and one active video.
Pause changed the video to paused. Navigation to Profile preserved collections
and stopped playback. Clicked/Saved toggles each produced one Profile entry.
Courses rendered sample labels and expanded the selected course topics.
The developer's unavailable-clip toggle produced the retry/skip error card;
skipping returned to the next clip with readyState 4 and advancing playback.
Two stable video surfaces were present: exactly one playing, the other paused
and preloaded. After watching two clips, remounting the feed showed three unseen
clips and excluded both watched identities. Fit/Fill changed the media object-fit
from contain to cover. At the end, Skip stayed on the final clip and an
explicit reload showed “You’re all caught up” without replaying the first clip.

The native iOS bundle launched through Expo on the booted iPhone 17 simulator.
Native UI automation then became stuck on the Simulator File-menu accessibility
state, so the redesigned native Reels playback is NOT marked verified. The user
reported that the app works and identified loading, repeat and framing issues;
those reports drove the fixes below. Physical-iPhone
playback, actual authenticated restart/logout and live Canvas OAuth remain open.

Live provider retrieval and browser fixture playback are separate results, not a
claim of fully verified live Reels playback through the redesigned native UI.

See [the API/storage decision](decisions/009-declic-ui-api-storage.md) for current
session-only behavior and the remaining durable API/runtime integration work.

## Reels loading, repetition and framing fixes

- Instagram continuation is sent in the POST body, matching the provider endpoint.
- Server reloads retain the continuation, unissued clips and 2,048 recent provider
  identities. Client history also excludes 2,048 recently selected identities
  across reloads and rolling-window eviction; deliberate Saved replay is allowed.
  This is bounded session history, not durable cross-device watch history.
- Prefetch begins with the initial short batch, transient API failures get two
  bounded retries, and ready media buffers switch without a new loading state.
- Two video surfaces remain mounted outside recycled list cells; late player
  callbacks are ignored. Navigation/background pause both drivers.
- The whole frame is shown by default, with explicit Fit/Fill control. Completing
  a batch no longer automatically restarts at its first video.
- The existing loopback API on port 8000 was restarted from this integration
  checkout, using the already-bound Instagram session. Expo preview is on 8094.
