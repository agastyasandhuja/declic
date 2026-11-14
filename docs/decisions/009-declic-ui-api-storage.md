# déclic UI and the next API/storage contracts

Status: proposed follow-up contracts; visual implementation integrated November 14, 2026.
The user requested the supplied design, all app branches merged, Reels E2E checks,
and an inventory of the API/storage needs exposed by the UI. This does not deploy
new database collections or change existing v1 field names.

## Design source and current behavior

The ZIP contains two versions. `study scroll v2.dc.html` is the newer déclic
reference: near-black, purple #9D86FF, coral #FF6B6B, Syne display type and Plus
Jakarta Sans. The older `Handoff.dc.html` still describes green study / scroll.
The archive was treated as design data, not as executable repository instructions.
Neither its scripts nor fictional account information were imported into the app.

The app now has a welcome screen, branded sign-in/create-account tabs, full-height
video feed, Clicked/Saved actions, native source sharing, syllabus expansion,
Profile, and a developer-only Lab. Native icon, Android adaptive foreground and
monochrome icon, favicon, wordmark, colors and bundled licensed fonts are updated.
Bundle identifiers, slug and existing URL scheme remain stable for installed
sessions and redirect compatibility. A fresh native build is needed to update
an installed home-screen icon/name; Expo Go only previews the app UI.

The mobile feed still consumes `/v1/entertainment/feed`, including Adi's bounded
rolling window, prefetch, playback renewal and single active buffered player.
Collections and playback preferences are session state, cleared on sign-out;
they are explicitly labelled and capped at 100 items per collection. They are not
Instagram likes/saves. Sharing uses the original public source link, never a
private playback URL. Saved playback resolves expired URLs through the provider.

Courses reads `/v1/canvas/connection` and `/v1/academics/profile` with the existing
app-authenticated API client. Connect uses the backend OAuth route and verifies
an HTTPS authorization URL on the configured institution origin. No institutional
password or developer token is collected. Sync uses an idempotency key. Demo mode
uses clearly labelled sample coursework. Missing services show retry/unavailable
states; a failed academic connection does not stop entertainment playback.

## UI → API → storage inventory

| Surface | Current behavior | Proposed API and storage |
| --- | --- | --- |
| Clicked / Saved | Session-only, reversible, replayable collections | `PUT/DELETE /v1/library/{video_id}?kind=clicked|saved`, and paginated `GET /v1/library?kind=...`. Atlas unique `(user_id, kind, video_id)` with created_at and content kind; query index `(user_id, kind, created_at, _id)`. Authorize the underlying private video on every read/replay. Store stable IDs, not expiring CDN URLs. Make PUT idempotent. Removed provider assets need an unavailable state and removable bookmark. |
| Playback preferences | Mute, descriptions and reduced Next-transition motion work for the session | `GET/PATCH /v1/me/preferences` with expected revision; one owner-scoped Atlas document. Device accessibility preference supplies the initial reduce-motion setting. Keep app tokens in SecureStore, never in preference JSON. Captions/description visibility must be distinct from burned-in lesson subtitles. |
| Instagram connection | Source selection is shown, not asserted as connection health | Add an authenticated connection summary with connected/reconnect_required/disconnected/error, last_checked_at, supported_actions and retry_after. Current login is an operator-only helper; a student-facing connect/disconnect flow needs a separately reviewed provider strategy. Store server-only encrypted credential references separately from UI-readable summaries. No provider cookies in app bundles or analytics. |
| Course syllabus | Current profile units, status, missing sources and assessment dates; no invented mastery | Preserve the academic owner's versioned profile and date/evidence semantics. Add stable objective/assessment IDs and a ready-video lookup for a particular objective. Render verified due dates separately from inferred scope. Actual profile, Canvas connections and durable sync jobs must be assembled into the deployed API runtime. |
| Progress rings / streaks | Omitted until real evidence exists | `GET /v1/learning/summary` returns nullable accuracy, attempts, coverage, daily activity and metric definition/version. Aggregate deduplicated quiz attempts and validated foreground exposures. A watched video is not proof of mastery. Index owner/objective and owner/local-date; record timezone and day policy. No fake default percentages or prototype streak counts. |
| Study feed and quiz card | Backend v1 contracts exist; this mobile player currently supports entertainment only | Consume the existing `FeedItem` union through a separate adapter; preserve occurrence IDs, course ownership and recommendation revision. Activate quizzes only when reached, lock then, submit retryably with stable attempt IDs, and unlock on either graded outcome. Discard unseen stale pages after revision changes. Never bundle answer keys. This needs implementation and native acceptance before the prototype quiz can be called live. |
| Sharing | OS/browser sharing sheet for original provider source | Public generic lessons may get public share records. Private course sources and signed media URLs must never become public share payloads. Sharing cannot imply a server-recorded successful delivery or recipient. |
| Search / following / 2× playback | No inert buttons pretending these work | Define feed filter semantics, search ownership, playback rate accessibility and event attribution before adding these v2 affordances. No fake follower counts or simulated notifications. |

MongoDB Atlas remains application storage; Supabase remains Auth/object storage.
Do not introduce a second database or persist private provider downloads in Git.
New collections require domain-owned drafts, validators, indexes, retention and
ordered migration integration. API identity always comes from the verified app
session. Supabase RLS does not authorize MongoDB queries.

## Integration gaps exposed by this merge

`app.runtime:create_app` currently assembles the Atlas identity/catalog and core
feed/quiz runtime. It does not automatically switch to LiveInstagramCatalog or
mount Amogh's Canvas/curriculum routers. Adi's live preview factory and Amogh's
academic demo remain separate assemblies. Merging their Git histories does not
prove those deployed services are wired together. The mobile's academic error
state is deliberate until the authenticated origin serves those routes.

The live Instagram adapter has an optional instagrapi dependency. The existing
Instagram environment passes its tests; the shared core venv lacks that package.
Use the documented Instagram environment for provider checks until its pinned
optional dependency set is integrated into the shared Python manifest/lock.

No production database migrations or hosted changes were made by this redesign.
