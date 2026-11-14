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
from ..timing import assessment_topics, target_topic_is_supported, upcoming_assessments
from ..sources import select_excerpts
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


def _exam_scope(exam_related: bool, assessments: list[dict]) -> str:
    if not exam_related:
        return "unknown"
    # explicit only if some assessment's scope is itself explicit
    if any(a.get("scope_status") == "user_confirmed" for a in assessments):
        return "user_confirmed"
    if any(a.get("scope_status") == "explicit" for a in assessments):
        return "explicit"
    return "inferred" if any(a.get("scope_status") == "inferred" for a in assessments) else "unknown"


def _assessment_ids(objective_title: str, assessments: list[dict]) -> list[str]:
    key = re.sub(r"\s+", " ", objective_title).strip().casefold()
    hits = []
    for a in assessments:
        topics = {" ".join(topic.casefold().split()) for topic in a.get("covered_topics", [])}
        if key in topics:
            hits.append(a["assessment_id"])
    return hits


def plan_course(course: dict, units: list[dict], assessments: list[dict], client: GeminiClient, sources=(), *, now=None) -> dict:
    """Assemble upcoming Canvas topics or run upload-fallback lesson planning."""
    timeline_required = bool(course.get("external_course_id"))
    now = now or datetime.now(timezone.utc)
    targets = upcoming_assessments(assessments, now, course.get("timezone")) if timeline_required else None
    if timeline_required:
        # Canvas has already supplied the deadline and the topic evidence. Carry
        # those forward directly into the handoff without a generative veto.
        raw = {"lessons": [
            {"objective_title": topic, "learning_goal": f"Review {topic}.",
             "target_assessment_id": target["assessment_id"], "target_topic": topic}
            for target in targets for topic in assessment_topics(target)
        ]}
        usage = {}
    else:
        prompt = build_plan_prompt(course, units, assessments, LESSON_FORMATS, sources)
        result = client.generate_json(
            system_instruction=SYSTEM_INSTRUCTION, user_content=prompt, response_schema=PLAN_SCHEMA
        )
        raw, usage = parse_json_object(result.text), result.usage
    course_id = course["course_id"]

    # First pass: title -> objective_id, so prerequisites can reference them.
    proposals = [p for p in (raw.get("lessons") or []) if isinstance(p, dict) and isinstance(p.get("objective_title"), str) and p["objective_title"].strip()]
    title_to_oid = {p["objective_title"].strip(): _oid(course_id, p["objective_title"]) for p in proposals}

    requests, seen = [], set()
    for proposal in proposals:
        title = proposal["objective_title"].strip()
        oid = title_to_oid[title]
        target = None
        if timeline_required:
            topic = proposal["target_topic"]
            target = next(item for item in targets if item["assessment_id"] == proposal["target_assessment_id"])

        if oid in seen:  # dedupe by meaning/level within the course
            continue
        seen.add(oid)

        is_practice = bool(proposal.get("is_suggested_practice"))
        exam_related = bool(proposal.get("exam_related")) and not is_practice
        unit_title = proposal.get("unit_title")
        matched_unit = next((u for u in units if isinstance(unit_title, str)
                             and u["title"].strip().casefold() == unit_title.strip().casefold()), {})
        source_refs = list(matched_unit.get("source_refs", []))
        formats = [f for f in (proposal.get("suggested_formats") or []) if f in LESSON_FORMATS] or ["visual_explainer"]
        prereq_ids = [title_to_oid[t] for t in (proposal.get("prerequisite_titles") or []) if isinstance(t, str) and t in title_to_oid and title_to_oid[t] != oid]
        importance = proposal.get("importance") if proposal.get("importance") in _IMPORTANCE else "supporting"

        if is_practice:
            evidence = "suggested_practice"
        elif source_refs:
            evidence = "explicit"
        else:
            evidence = "inferred"

        linked_ids = _assessment_ids(title, assessments) if exam_related else []
        if target:
            supporting = [item for item in targets if target_topic_is_supported(topic, item)]
            linked_ids = [item["assessment_id"] for item in supporting]
            source_refs = list(dict.fromkeys(
                ref for item in supporting
                for ref in item.get("source_refs", []) + item["scheduled"].get("source_refs", [])
            ))
            evidence = "explicit"
        linked = [a for a in assessments if a["assessment_id"] in linked_ids]
        exam_links = [a for a in linked if a["kind"] in {"midterm", "final"} or a.get("is_exam")]

        requests.append(
            {
                "lesson_request_id": "lr_" + hashlib.sha256(f"{course_id}\x1f{oid}".encode()).hexdigest()[:12],
                "objective_id": oid,
                "binding_id": "bind_" + hashlib.sha256(f"{course_id}\x1f{oid}".encode()).hexdigest()[:12],
                "unit_id": matched_unit.get("unit_id"),
                "title": topic if target else title,
                "learning_goal": proposal.get("learning_goal", "") if isinstance(proposal.get("learning_goal"), str) else "",
                "prerequisite_objective_ids": prereq_ids,
                "source_refs": source_refs,
                "evidence_status": evidence,
                "exam_scope_status": _exam_scope(bool(exam_links), exam_links) if target else _exam_scope(bool(linked), linked),
                **({"timeline_topic": topic} if target else {}),
                "assessment_ids": linked_ids,
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

        if not timeline_required and len(requests) == 3:
            break

    requested_ids = {request["objective_id"] for request in requests}
    for request in requests:
        request["prerequisite_objective_ids"] = [
            oid for oid in request["prerequisite_objective_ids"] if oid in requested_ids
        ]

    plan_id = "plan_" + hashlib.sha256(course_id.encode()).hexdigest()[:12]
    return {
        "schema_version": SCHEMA_VERSION,
        "plan_id": plan_id,
        "course_id": course_id,
        "revision": 1,
        "status": "validated",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "requests": requests,
        "warnings": ["No lesson matched a verified upcoming target"] if timeline_required and not requests else [],
        "usage": usage,
    }


def build_lesson_plans(profile: dict, client: GeminiClient, resolver=None) -> list[dict]:
    """Plan every ready course in the profile. One failing course is skipped
    with a warning recorded on the returned plan (empty requests)."""
    plans = []
    now = datetime.now(timezone.utc)
    for course in profile["courses"]:
        if course.get("import_status") not in {"ready", "partial"}:
            continue
        course_id = course["course_id"]
        units = [u for u in profile["units"] if u["course_id"] == course_id]
        assessments = [a for a in profile["assessments"] if a["course_id"] == course_id]
        try:
            sources = []
            if resolver and not course.get("external_course_id"):
                read = getattr(resolver, "sources_for_planning", resolver.sources_for_course)
                sources = select_excerpts(read(course_id), 16_000)
            plan = plan_course(course, units, assessments, client, sources, now=now)
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
