"""Prompt building for M4 lesson planning (owner: Amogh).

Gemini proposes short, teachable objectives from an already-validated course
profile. The model proposes; the backend validates. Suggested practice must stay
separate from confirmed exam coverage.
"""

from __future__ import annotations

import json

SYSTEM_INSTRUCTION = (
    "You plan short study videos (30-60 seconds each) from a validated course "
    "profile. Rules:\n"
    "1. Propose 2-3 of the most useful objectives for this course, prioritizing "
    "near-term units and confirmed exam scope. Each objective must be small "
    "enough to teach in 30-60 seconds.\n"
    "2. Split broad topics: e.g. 'introduction to linked lists' and 'iterative "
    "reversal of a linked list' are SEPARATE objectives, not one.\n"
    "3. Set is_suggested_practice=true for enrichment or practice that is NOT "
    "confirmed exam coverage. Never label suggested practice as exam-related.\n"
    "4. Set exam_related=true only when the profile's assessments actually cover "
    "the topic. If unsure, false.\n"
    "5. Identify prerequisite objectives by title so they can be taught first.\n"
    "6. Choose suggested_formats only from the allowed list given.\n"
    "7. target_duration_seconds must be between 30 and 60.\n"
    "Return only the JSON object required by the schema."
)


def build_plan_prompt(course: dict, units: list[dict], assessments: list[dict], formats: list[str]) -> str:
    """Give Gemini the validated, already-sourced course profile as compact JSON."""
    compact = {
        "course_title": course.get("title"),
        "term": course.get("term"),
        "units": [
            {"title": u["title"], "order": u["order"], "objectives": u["objectives"]}
            for u in units
        ],
        "assessments": [
            {
                "title": a["title"],
                "kind": a["kind"],
                "date": a["scheduled"]["date"],
                "scope_status": a["scope_status"],
                "covered_topics": a["covered_topics"],
            }
            for a in assessments
        ],
    }
    focus = ""
    timing = course.get("timing")
    if timing and timing.get("upcoming"):
        soon = "; ".join(f"{i['due_date']} ({i['days_until']}d): {i['name']}" for i in timing["upcoming"][:5])
        focus = (
            "\n\nREAL-TIME PRIORITY — this student's nearest upcoming graded work "
            f"(as of today): {soon}.\nPrioritize objectives that help with this "
            "upcoming work. Do not invent exam dates.\n"
        )
    return (
        f"Allowed suggested_formats: {', '.join(formats)}\n\n"
        f"Validated course profile:\n{json.dumps(compact, indent=2)}{focus}\n\n"
        "Propose the lesson objectives as instructed. Keep suggested practice "
        "separate from confirmed exam coverage."
    )
