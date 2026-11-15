# Unified feed, session and feedback contract

Owner: Agastya. UI consumer: Adi.

## Session

POST /v1/feed/sessions with optional resume_session_id returns:
schema_version, session_id, started_at, last_active_at, active_view_seconds,
study_ratio_target, recommendation_revision, pending_quiz_instance_id.

Server verifies session ownership. A session resumes within the configured idle
window, rather than resetting the ramp on every refresh.

## Feed

GET /v1/feed?session_id=&cursor=&limit= returns:
schema_version, session_id, recommendation_revision, items, next_cursor,
pending_quiz_instance_id.

Each item has item_id (unique occurrence ID), kind, inserted_at, reason_codes,
and exactly one payload:

| kind | payload |
|---|---|
| entertainment_video | video: normalized EntertainmentVideo |
| study_video | video: ready VideoVariant summary, course_context: {course_id, title, objective_id}, reason_text |
| quiz | quiz: QuizCard |

Occurrence IDs are not video IDs: the same reusable asset can appear in different
sessions/users. Course context is authorized per user even for a shared video.

Ordering rules:

- Only ready, authorized, playable assets are returned.
- A pending quiz is returned before further consumable items. Server does not
  issue post-quiz pages until answer/recovery.
- A quiz planned in a future page becomes pending when the user reaches it;
  do not lock the current video just because the next quiz was prefetched.
- Client activates the quiz using POST /v1/feed/sessions/{session_id}/quiz-gate
  with quiz_instance_id and item_id. Server verifies it was issued to the session
  and is the next required gate. Activation is idempotent.
  Returns session_id, pending_quiz_instance_id, scroll_locked and
  recommendation_revision. A resolved gate returns scroll_locked: false;
  the client must not relock it because an activation request was retried.
- No feed page includes playable items after a quiz boundary; next_cursor can
  resume only after the gate is resolved.
- After an answer, increment recommendation_revision. Return 409 STALE_CURSOR
  for an old revision cursor. Mobile drops unseen items and fetches a new page.
- If study inventory is empty, fill with entertainment and report availability;
  do not synchronously generate or accumulate unbounded study debt.

## Events

POST /v1/feed/events accepts a bounded list:

event_id, session_id, item_id, event_type, client_occurred_at, payload.

event_type values: playback_started, playback_progress, playback_completed,
video_skipped, playback_failed, app_backgrounded, app_foregrounded.
Playback payload includes position_ms and visible_watch_ms where applicable.
Do not send full provider cookies, source documents or answer keys.

Server deduplicates event_id and validates ownership, item issuance, plausible
time ranges and monotonic progress. Active time is accumulated from valid
foreground playback, not wall-clock session age or a trusted client total.
Returns accepted_event_ids and rejected [{event_id, code}].
Events may be retried after temporary network failure.

## Reason codes

Examples: entertainment_slot, current_unit, upcoming_exam, quiz_weakness,
review_due, course_diversity, new_explanation, inventory_fallback.
User-facing reason text must not claim confirmed exam scope from inferred evidence.

## Synthetic response example

```json
{
  "schema_version": "1",
  "session_id": "session_demo_01",
  "recommendation_revision": 2,
  "items": [
    {
      "item_id": "occurrence_demo_10",
      "kind": "quiz",
      "inserted_at": "2026-11-13T22:00:00Z",
      "reason_codes": ["review_due"],
      "quiz": {
        "quiz_instance_id": "quiz_instance_demo_01",
        "quiz_id": "quiz_demo_reverse",
        "revision": 1,
        "objective_ids": ["objective_demo_reverse"],
        "prompt": "Before changing current.next during reversal, what must you save?",
        "options": [
          {"option_id": "a", "text": "The original next node"},
          {"option_id": "b", "text": "The length of the entire list"}
        ],
        "related_video_ids": ["video_demo_reverse_01"]
      }
    }
  ],
  "next_cursor": null,
  "pending_quiz_instance_id": "quiz_instance_demo_01"
}
```

The correct answer is intentionally absent from this payload.

## Explicit seeking and curriculum switching

`playback_seeked` is an additive playback event. Mobile first flushes preceding
progress, sends the intended `position_ms` with **unchanged** last-reported
`visible_watch_ms`, then waits for acknowledgement and actual player position
settling before reporting more progress. The server requires an active owned
foreground occurrence, validates duration bounds, accepts the position regression,
awards zero watch/active/exposure credit and resets time anchors. Ordinary progress
still cannot move backwards. Playback speed never multiplies wall-visible credit.

Account-level demo mode and its ungraded old-gate recovery are specified in
[the shared demo contract](demo-catalog.md). Mode changes reject late playback
from the previous curriculum, including started cards. Old quiz answers cannot
create a new grade after the gate was recovered.

## Cold-start bootstrap (November 14)

`POST /v1/feed/bootstrap` accepts `{limit: 5, preferred_video_ids: []}` and an
`Idempotency-Key`; it returns the existing Feed response shape directly. The
optional hint list has at most six entertainment video IDs, never URLs or user
IDs. Session resume/refresh and first-page issuance share one owner-scoped
transaction. A retry with the same key/body revalidates the same page; a changed
request conflicts, and an obsolete recommendation revision returns
`409 STALE_BOOTSTRAP` so the client can start again with a new key.

On app opening, bootstrap returns one regular reel among currently authorized,
ready, nonexpired entertainment candidates, excluding the immediately previous
clip. Cache hints prefer a matching eligible reel. Course/video inventory and
new quiz selection wait for the following mixed page, so they do not delay the
first reel. Existing study debt is preserved for that page. Scheduled or active
quiz gates survive reopening and take precedence. If no regular reel is ready,
startup returns retryable `503 ENTERTAINMENT_UNAVAILABLE` rather than substituting
a study video. The one-item startup response still binds its cursor to the
requested page size; subsequent mixed cursor reads use that same size. Clients may resolve
a freshly authorized clip to a completed local cache file scoped to the same
account/API and still within its cache lifetime; hints themselves grant no
playback authorization or learning credit.
