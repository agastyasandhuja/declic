"""M4 lesson planning (owner: Amogh).

Takes a validated AcademicProfile (from M3) and, per course, asks Gemini to
propose short lesson objectives. The backend then assembles contract LessonPlan
and LessonRequest records (contracts/academics.md), keeping suggested practice
separate from confirmed exam coverage.

Gemini proposes pedagogy; deterministic code assigns IDs, source references,
evidence/scope status and scope. The model never sees tokens or the database.
"""

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone

from ..client.gemini import GeminiClient, parse_json_object
from ..prompts.plan import SYSTEM_INSTRUCTION, build_plan_prompt
from ..schemas import LESSON_FORMATS, PLAN_SCHEMA, SCHEMA_VERSION

_IMPORTANCE = {"core", "supporting", "optional"}
DEFAULT_VARIANT_COUNT = 2


def _oid(course_id: str, title: str) -> str:
    key = re.sub(r"\s+", " ", title).strip().lower()
    return "obj_" + hashlib.sha256(f"{course_id}\x1f{key}".encode()).hexdigest()[:12]


def _clamp_duration(value) -> int:
    try:
        seconds = int(value)
    except (TypeError, ValueError):
        return 45
    return max(30, min(60, seconds))


def _source_refs_for_unit(unit_title: str, units: list[dict]) -> list[str]:
    key = re.sub(r"\s+", " ", unit_title or "").strip().lower()
    for unit in units:
        if re.sub(r"\s+", " ", unit["title"]).strip().lower() == key:
            return list(unit.get("source_refs", []))
    return []


def _exam_scope(exam_related: bool, assessments: list[dict]) -> str:
    if not exam_related:
        return "unknown"
    # explicit only if some assessment's scope is itself explicit
    if any(a.get("scope_status") == "explicit" for a in assessments):
        return "explicit"
    return "inferred"


def _assessment_ids(objective_title: str, assessments: list[dict]) -> list[str]:
    key = re.sub(r"\s+", " ", objective_title).strip().lower()
    hits = []
    for a in assessments:
        topics = " ".join(a.get("covered_topics", [])).lower()
        if key in topics or any(w in topics for w in key.split() if len(w) > 4):
            hits.append(a["assessment_id"])
    return hits


def plan_course(course: dict, units: list[dict], assessments: list[dict], client: GeminiClient) -> dict:
    """Run one Gemini planning call for a course and assemble a validated plan."""
    prompt = build_plan_prompt(course, units, assessments, LESSON_FORMATS)
    result = client.generate_json(
        system_instruction=SYSTEM_INSTRUCTION, user_content=prompt, response_schema=PLAN_SCHEMA
    )
    raw = parse_json_object(result.text)
    course_id = course["course_id"]

    # First pass: title -> objective_id, so prerequisites can reference them.
    proposals = [p for p in (raw.get("lessons") or []) if isinstance(p, dict) and isinstance(p.get("objective_title"), str)]
    title_to_oid = {p["objective_title"]: _oid(course_id, p["objective_title"]) for p in proposals}

    requests, seen = [], set()
    for proposal in proposals:
        title = proposal["objective_title"].strip()
        oid = title_to_oid[title]
        if oid in seen:  # dedupe by meaning/level within the course
            continue
        seen.add(oid)

        is_practice = bool(proposal.get("is_suggested_practice"))
        exam_related = bool(proposal.get("exam_related")) and not is_practice
        source_refs = _source_refs_for_unit(proposal.get("unit_title", ""), units)
        formats = [f for f in (proposal.get("suggested_formats") or []) if f in LESSON_FORMATS] or ["visual_explainer"]
        prereq_ids = [title_to_oid[t] for t in (proposal.get("prerequisite_titles") or []) if t in title_to_oid and title_to_oid[t] != oid]
        importance = proposal.get("importance") if proposal.get("importance") in _IMPORTANCE else "supporting"

        if is_practice:
            evidence = "suggested_practice"
        elif source_refs:
            evidence = "explicit"
        else:
            evidence = "inferred"

        requests.append(
            {
                "lesson_request_id": "lr_" + hashlib.sha256(f"{course_id}\x1f{oid}".encode()).hexdigest()[:12],
                "objective_id": oid,
                "binding_id": "bind_" + hashlib.sha256(f"{course_id}\x1f{oid}".encode()).hexdigest()[:12],
                "title": title,
                "learning_goal": proposal.get("learning_goal", "") if isinstance(proposal.get("learning_goal"), str) else "",
                "prerequisite_objective_ids": prereq_ids,
                "source_refs": source_refs,
                "evidence_status": evidence,
                "exam_scope_status": _exam_scope(exam_related, assessments),
                "assessment_ids": _assessment_ids(title, assessments) if exam_related else [],
                "importance": importance,
                "suggested_formats": formats,
                "teaching_approaches": [t for t in (proposal.get("teaching_approaches") or []) if isinstance(t, str)],
                "target_duration_seconds": _clamp_duration(proposal.get("target_duration_seconds")),
                "desired_variant_count": DEFAULT_VARIANT_COUNT,
                "generic_brief": None,
                "private_context_ref": None,
                "scope": "private",
                "warnings": [],
            }
        )

    plan_id = "plan_" + hashlib.sha256(course_id.encode()).hexdigest()[:12]
    return {
        "schema_version": SCHEMA_VERSION,
        "plan_id": plan_id,
        "course_id": course_id,
        "revision": 1,
        "status": "validated",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "requests": requests,
        "usage": result.usage,
    }


def build_lesson_plans(profile: dict, client: GeminiClient) -> list[dict]:
    """Plan every ready course in the profile. One failing course is skipped
    with a warning recorded on the returned plan (empty requests)."""
    plans = []
    for course in profile["courses"]:
        if course.get("import_status") != "ready":
            continue
        course_id = course["course_id"]
        units = [u for u in profile["units"] if u["course_id"] == course_id]
        assessments = [a for a in profile["assessments"] if a["course_id"] == course_id]
        try:
            plan = plan_course(course, units, assessments, client)
        except Exception as err:  # noqa: BLE001 — isolate one course
            plan = {
                "schema_version": SCHEMA_VERSION,
                "plan_id": "plan_" + hashlib.sha256(course_id.encode()).hexdigest()[:12],
                "course_id": course_id, "revision": 1, "status": "draft",
                "created_at": datetime.now(timezone.utc).isoformat(), "requests": [],
                "usage": {}, "warnings": [f"planning failed ({type(err).__name__})"],
            }
        plan.setdefault("profile_id", profile["profile_id"])
        plan.setdefault("profile_revision", profile["revision"])
        plan.setdefault("user_id", profile["user_id"])
        plans.append(plan)
    return plans
