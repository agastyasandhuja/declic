"""M3 pipeline: resolve a user's sources, call Gemini per course, validate the
result, and assemble a versioned AcademicProfile (owner: Amogh).

Public entry point: build_profile(user_id, storage_dir, client). The Gemini
client is injected so tests can run with a fake and never touch the network.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path

from .client.gemini import GeminiClient, parse_json_object
from .prompts.extract import SYSTEM_INSTRUCTION, build_extraction_prompt
from .schemas import EXTRACTION_SCHEMA, SCHEMA_VERSION
from .sources import Resolver
from .store import latest_revision, save_profile
from .validators import validate_extraction


def _sid(*parts: str) -> str:
    return hashlib.sha256("\x1f".join(parts).encode()).hexdigest()[:12]


def extract_course(
    course_id: str, resolver: Resolver, client: GeminiClient
) -> dict:
    """Run one real Gemini extraction for a single course and validate it."""
    sources = resolver.sources_for_course(course_id)
    authorized_ids = {s.source_id for s in sources}
    usable = [s for s in sources if s.has_text]

    if not usable:
        return {
            "course_id": course_id,
            "import_status": "needs_review",
            "extraction": None,
            "warnings": ["no extractable source text for this course (upload a .txt/.md syllabus)"],
            "usage": {},
        }

    label_hint = usable[0].title
    prompt = build_extraction_prompt(label_hint, usable)
    result = client.generate_json(
        system_instruction=SYSTEM_INSTRUCTION,
        user_content=prompt,
        response_schema=EXTRACTION_SCHEMA,
    )
    raw = parse_json_object(result.text)
    clean = validate_extraction(raw, authorized_ids)
    return {
        "course_id": course_id,
        "import_status": "ready",
        "extraction": clean,
        "warnings": clean["warnings"],
        "usage": result.usage,
    }


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
    course_ids = resolver.course_ids()
    if not course_ids:
        raise ValueError("no sources available for this user (no Canvas courses or uploads)")

    revision = latest_revision(storage_dir, user_id) + 1
    profile_id = f"prof_{_sid(user_id)}"
    generated_at = datetime.now(timezone.utc).isoformat()

    courses, units, assessments, warnings = [], [], [], []
    total_usage = {"prompt_tokens": 0, "candidates_tokens": 0}

    for course_id in course_ids:
        try:
            outcome = extract_course(course_id, resolver, client)
        except Exception as err:  # noqa: BLE001 — isolate one course's failure
            warnings.append(f"course {course_id}: extraction failed ({type(err).__name__})")
            courses.append({"course_id": course_id, "import_status": "error", "title": None})
            continue

        usage = outcome.get("usage") or {}
        total_usage["prompt_tokens"] += usage.get("promptTokenCount", 0)
        total_usage["candidates_tokens"] += usage.get("candidatesTokenCount", 0)
        warnings.extend(f"{course_id}: {w}" for w in outcome["warnings"])

        extraction = outcome["extraction"]
        if extraction is None:
            courses.append({"course_id": course_id, "import_status": outcome["import_status"], "title": None})
            continue

        courses.append(
            {
                "course_id": course_id,
                "import_status": outcome["import_status"],
                "title": extraction["course_title"],
                "term": extraction["term"],
                "timezone": extraction["timezone"],
                "textbooks": extraction["textbooks"],
            }
        )
        for unit in extraction["units"]:
            units.append({"unit_id": f"unit_{_sid(course_id, unit['title'], str(unit['order']))}", "course_id": course_id, **unit})
        for assessment in extraction["assessments"]:
            assessments.append({"assessment_id": f"asmt_{_sid(course_id, assessment['title'])}", "course_id": course_id, **assessment})

    profile = {
        "schema_version": SCHEMA_VERSION,
        "profile_id": profile_id,
        "user_id": user_id,
        "revision": revision,
        "status": "validated",
        "generated_at": generated_at,
        "course_ids": course_ids,
        "courses": courses,
        "units": units,
        "assessments": assessments,
        "binding_ids": [],
        "lesson_plan_ids": [],
        "warnings": warnings,
        "usage": total_usage,
    }
    if persist:
        save_profile(storage_dir, user_id, profile)
    return profile
