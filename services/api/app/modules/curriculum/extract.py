"""M3 pipeline: resolve a user's sources, call Gemini per course, validate the
result, and assemble a versioned AcademicProfile (owner: Amogh).

Public entry point: build_profile(user_id, storage_dir, client). The Gemini
client is injected so tests can run with a fake and never touch the network.
"""

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from ..canvas.client.http import CanvasAuthError
from .client.gemini import GeminiClient, GeminiError, parse_json_object
from .prompts.extract import SYSTEM_INSTRUCTION, build_extraction_prompt
from .schemas import EXTRACTION_SCHEMA, SCHEMA_VERSION
from .sources import Resolver
from .retrieval import gather_evidence
from .store import latest_revision, save_profile
from .validators import validate_extraction
from .timing import _parse


def _title_key(title: str) -> str:
    return " ".join(title.casefold().split())


def _sid(*parts: str) -> str:
    return hashlib.sha256("\x1f".join(parts).encode()).hexdigest()[:12]


def _course_fingerprint(resolver: Resolver, course_id: str) -> str:
    """A stable signature of a course's sources for reimport dedup. Uses each
    source's content hash when known, else its Canvas updated_at, plus assignment
    due dates (they drive assessments). If nothing changed, the signature is the
    same and the prior extraction can be reused instead of re-calling Gemini."""
    # Invalidate maps produced before PDF text became a required dependency.
    parts = ["source-extraction-v2-pdf-text"]
    for source in resolver.sources_for_course(course_id):
        stamp = source.content_hash or source.source_updated_at or ""
        parts.append(f"{source.source_id}:{stamp}:{source.title}:{source.locator}")
    getter = getattr(resolver, "assignments_for_course", None)
    if getter:
        for assignment in getter(course_id):
            parts.append(f"a:{assignment.external_id}:{assignment.due_at}")
    return hashlib.sha256("\x1f".join(sorted(parts)).encode()).hexdigest()[:16]


def extract_course(
    course_id: str, resolver: Resolver, client: GeminiClient
) -> dict:
    """Run one real Gemini extraction for a single course and validate it."""
    sources = resolver.sources_for_course(course_id)
    usable, media, retrieval_warnings = gather_evidence(course_id, resolver, sources, client)
    evidence = {s.source_id: s.text for s in usable}

    if not usable and not media:
        return {
            "course_id": course_id,
            "import_status": "needs_review",
            "extraction": None,
            "warnings": ["no extractable source text for this course (upload a .txt/.md syllabus)"],
            "usage": {},
        }

    label_hint = sources[0].title
    prompt = build_extraction_prompt(label_hint, usable)
    request = dict(system_instruction=SYSTEM_INSTRUCTION, user_content=prompt,
                   response_schema=EXTRACTION_SCHEMA)
    if media:
        try:
            result = client.generate_json(**request, media=media)
        except GeminiError:
            media = ()
            if not usable:
                raise
            retrieval_warnings.append("Gemini could not read attachments; used text excerpts")
            result = client.generate_json(**request)
    else:
        result = client.generate_json(**request)
    raw = parse_json_object(result.text)
    clean = validate_extraction(raw, set(evidence) | {item[0] for item in media}, evidence=evidence,
                                source_timezone=_course_info(resolver, course_id).get("timezone"))
    return {
        "course_id": course_id,
        "import_status": "ready",
        "extraction": clean,
        "warnings": retrieval_warnings + clean["warnings"],
        "usage": result.usage,
    }


def _course_info(resolver, course_id):
    getter = getattr(resolver, "course_info", None)
    return getter(course_id) if getter else {}


def build_profile(
    user_id: str,
    resolver: Resolver,
    client: GeminiClient,
    storage_dir: Path,
    *,
    persist: bool = True,
) -> dict:
    """Extract every course the resolver exposes and assemble a profile.

    The resolver is injected: CanvasSourceResolver (primary, live Canvas) or the
    upload-store SourceResolver (fallback). One failing course does not abort the
    others; its status is recorded.
    """
    owner = getattr(resolver, "owner_user_id", None)
    if owner is not None and owner != user_id:
        raise PermissionError("source resolver owner mismatch")
    course_ids = resolver.course_ids()
    if not course_ids:
        raise ValueError("no sources available for this user (no Canvas courses or uploads)")

    revision = latest_revision(storage_dir, user_id) + 1
    profile_id = f"prof_{_sid(user_id)}"
    generated_at = datetime.now(timezone.utc).isoformat()

    # Reimport dedup: reuse the prior extraction for a course whose sources are
    # unchanged, so Gemini is not re-run on identical material.
    from .store import load_profile

    previous = load_profile(storage_dir, user_id) or {}
    prev_courses = {c["course_id"]: c for c in previous.get("courses", [])}
    prev_units: dict[str, list] = {}
    for unit in previous.get("units", []):
        prev_units.setdefault(unit["course_id"], []).append(unit)
    prev_assessments: dict[str, list] = {}
    for item in previous.get("assessments", []):
        prev_assessments.setdefault(item["course_id"], []).append(item)

    courses, units, assessments, warnings = [], [], [], []
    total_usage = {"prompt_tokens": 0, "candidates_tokens": 0}

    from concurrent.futures import ThreadPoolExecutor

    fingerprints = {cid: _course_fingerprint(resolver, cid) for cid in course_ids}
    with ThreadPoolExecutor(max_workers=3) as pool:
        outcomes = {cid: pool.submit(extract_course, cid, resolver, client)
                    for cid in course_ids
                    if not (prev_courses.get(cid, {}).get("sources_fingerprint") == fingerprints[cid]
                            and prev_courses.get(cid, {}).get("import_status") in {"ready", "partial"})}
    for course_id in course_ids:
        info = _course_info(resolver, course_id)
        fingerprint = fingerprints[course_id]
        prior = prev_courses.get(course_id)
        if (prior and prior.get("sources_fingerprint") == fingerprint
                and prior.get("import_status") in {"ready", "partial"}):
            restore = getattr(resolver, "restore_extracted_sources", None)
            if restore:
                restore(course_id, previous.get("_sources", []))
            courses.append({**prior, "sources_fingerprint": fingerprint})
            units.extend(prev_units.get(course_id, []))
            assessments.extend(prev_assessments.get(course_id, []))
            warnings.append(f"{course_id}: reused unchanged sources (no re-extraction)")
            continue
        try:
            outcome = outcomes[course_id].result()
        except CanvasAuthError:
            raise
        except Exception as err:  # noqa: BLE001 — isolate one course's failure
            warnings.append(f"course {course_id}: extraction failed ({type(err).__name__})")
            if not info.get("external_course_id"):
                courses.append({"course_id": course_id, "import_status": "error", "title": None,
                                "sources_fingerprint": fingerprint, **info})
                continue
            outcome = {
                "import_status": "partial", "warnings": [],
                "extraction": {"course_title": info.get("title"), "term": info.get("term"),
                               "timezone": info.get("timezone"), "textbooks": [],
                               "units": [], "assessments": []},
            }

        usage = outcome.get("usage") or {}
        total_usage["prompt_tokens"] += usage.get("promptTokenCount", 0)
        total_usage["candidates_tokens"] += usage.get("candidatesTokenCount", 0)
        warnings.extend(f"{course_id}: {w}" for w in outcome["warnings"])

        extraction = outcome["extraction"]
        if extraction is None:
            courses.append({"course_id": course_id, "import_status": outcome["import_status"],
                            "title": None, "sources_fingerprint": fingerprint, **info})
            continue

        courses.append(
            {
                "course_id": course_id,
                "import_status": outcome["import_status"],
                "sources_fingerprint": fingerprint,
                "title": extraction["course_title"],
                "term": extraction["term"],
                "timezone": extraction["timezone"],
                "textbooks": extraction["textbooks"],
                "source_inventory": [
                    {"source_id": source.source_id, "title": source.title,
                     "resource_type": source.resource_type, "locator": source.locator}
                    for source in resolver.sources_for_course(course_id)
                ],
                **{key: value for key, value in info.items() if value is not None},
            }
        )
        for unit in extraction["units"]:
            units.append({"unit_id": f"unit_{_sid(course_id, unit['title'], str(unit['order']))}", "course_id": course_id, **unit})
        by_title = {_title_key(item["title"]): item for item in extraction["assessments"]}
        if hasattr(resolver, "assignments_for_course"):
            course_sources = resolver.sources_for_course(course_id)
            overview_id = course_sources[0].source_id
            assignment_sources = {source.external_id: source.source_id for source in course_sources
                                  if source.resource_type == "assignment"}
            for assignment in resolver.assignments_for_course(course_id):
                key = _title_key(assignment.name)
                due = _parse(assignment.due_at)
                if not key or (not due and not assignment.looks_like_exam):
                    continue
                kind = ("midterm" if "midterm" in key else "final" if "final" in key
                        else "other" if assignment.looks_like_exam else "assignment")
                assignment_ref = assignment_sources.get(assignment.external_id, overview_id)
                item = by_title.setdefault(key, {
                    "title": assignment.name, "scope_status": "unknown", "covered_topics": [],
                    "source_refs": [assignment_ref], "scheduled": {},
                })
                if kind == "assignment" and re.match(r"^quiz\b", key):
                    kind = "quiz"
                item["kind"] = kind
                if assignment.looks_like_exam:
                    item["is_exam"] = True
                if item.get("date_conflict"):
                    continue
                zone = info.get("timezone") or extraction["timezone"]
                if due and due.utcoffset() is not None:
                    try:
                        due = due.astimezone(ZoneInfo(zone)) if zone else due
                    except (ValueError, ZoneInfoNotFoundError):
                        zone = None
                    existing = item["scheduled"].get("date")
                    # Compare the local date after normalizing source timestamps.
                    if assignment.looks_like_exam and existing and existing != due.date().isoformat():
                        item["date_conflict"] = True
                        warnings.append(f"{course_id}: conflicting assessment schedule")
                        item["scheduled"] = {}
                    else:
                        item["scheduled"] = {
                            "date": due.date().isoformat(), "timestamp": due.isoformat(),
                            "timezone": zone, "precision": "datetime", "evidence_status": "explicit",
                            "source_refs": [assignment_ref],
                        }
                if not item["scheduled"]:
                    item["scheduled"] = {
                        "date": None, "timestamp": None, "timezone": zone,
                        "precision": "unknown", "evidence_status": "unknown", "source_refs": [],
                    }
        for key, assessment in by_title.items():
            kind = assessment["kind"]
            if kind == "other":
                if re.search(r"\bmidterms?\b", key):
                    assessment["kind"] = "midterm"
                elif re.search(r"\bfinal(?: exam)?\b", key):
                    assessment["kind"] = "final"
                elif re.search(r"\b(?:exam|test)\b", key):
                    assessment["is_exam"] = True
            assessments.append({"assessment_id": f"asmt_{_sid(course_id, key)}", "course_id": course_id, **assessment})

    profile = {
        "schema_version": SCHEMA_VERSION,
        "profile_id": profile_id,
        "user_id": user_id,
        "revision": revision,
        "status": "validated",
        "generated_at": generated_at,
        "course_ids": course_ids,
        "unit_ids": [unit["unit_id"] for unit in units],
        "assessment_ids": [item["assessment_id"] for item in assessments],
        "courses": courses,
        "units": units,
        "assessments": assessments,
        "binding_ids": [],
        "lesson_plan_ids": [],
        "warnings": warnings,
        "usage": total_usage,
    }
    from .corrections import restore_corrections

    if persist:
        save_profile(storage_dir, user_id, profile, reimport=True)
    else:
        restore_corrections(storage_dir, user_id, profile)
    return profile
