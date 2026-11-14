"""Handoff to Agastya (owner: Amogh).

Per contracts/academics.md, publishing a validated profile revision emits
`academics.profile.ready` carrying profile_id, revision, course_ids and plan_ids.
There is no shared event bus yet (API core is not initialized), so this builds
the event payload; the dispatch is wired when core/jobs exist.
"""

from __future__ import annotations


def build_profile_ready_event(profile: dict, plans: list[dict]) -> dict:
    """The academics.profile.ready payload for a validated profile + its plans."""
    return {
        "event": "academics.profile.ready",
        "profile_id": profile["profile_id"],
        "revision": profile["revision"],
        "user_id": profile["user_id"],
        "course_ids": profile["course_ids"],
        "plan_ids": [p["plan_id"] for p in plans if p.get("requests")],
        "generated_at": profile.get("generated_at"),
    }
