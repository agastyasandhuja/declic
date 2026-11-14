"""Validate explicit student overrides and carry them across imports."""
from datetime import datetime, timezone

from .validators import _valid_date


class RevisionConflict(ValueError):
    pass


def apply_overrides(profile):
    for assessment in profile.get("assessments", []):
        change = profile.get("manual_corrections", {}).get(assessment["assessment_id"])
        if change is None:
            continue
        if "date" in change:
            value = change["date"]
            assessment["scheduled"] = {
                "date": value, "timestamp": None,
                "timezone": assessment["scheduled"].get("timezone"),
                "precision": "date" if value else "unknown",
                "evidence_status": "user_confirmed", "source_refs": [],
            }
        if "scope_status" in change:
            assessment["scope_status"] = change["scope_status"]


def restore_corrections(storage_dir, user_id, profile):
    from .store import load_profile

    previous = load_profile(storage_dir, user_id) or {}
    profile["manual_corrections"] = previous.get("manual_corrections", {})
    apply_overrides(profile)


def correct_profile(profile, revision, changes):
    if profile["revision"] != revision:
        raise RevisionConflict("profile revision is stale")
    ids = {assessment["assessment_id"] for assessment in profile["assessments"]}
    overrides = profile.setdefault("manual_corrections", {})
    for change in changes:
        if (not isinstance(change, dict) or set(change) - {"assessment_id", "date", "scope_status"}
                or not isinstance(change.get("assessment_id"), str) or len(change) < 2):
            raise ValueError("invalid correction")
        assessment_id = change["assessment_id"]
        if assessment_id not in ids:
            raise LookupError("assessment unavailable")
        if "date" in change and change["date"] is not None and not _valid_date(change["date"]):
            raise ValueError("invalid correction date")
        if "scope_status" in change and change["scope_status"] not in (
            "explicit", "inferred", "unknown", "user_confirmed"
        ):
            raise ValueError("invalid scope status")
        overrides.setdefault(assessment_id, {}).update(
            {key: value for key, value in change.items() if key != "assessment_id"}
        )
    apply_overrides(profile)
    profile["revision"] += 1
    profile["generated_at"] = datetime.now(timezone.utc).isoformat()
    profile["lesson_plan_ids"] = []
    profile["binding_ids"] = []
    return profile
