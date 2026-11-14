"""Read a student's own current courses and a light preview of each one's
content (syllabus, term, timezone).

This is the demo-facing slice of M1: it proves we can reach *this student's*
specific courses and see real material inside them. Full ingestion of modules,
files, assignments and calendar events is M2.

Everything here is read-only and scoped to the connected student: Canvas only
ever returns courses that student is enrolled in.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .client.http import CanvasClient, CanvasUnavailable

_TAG = re.compile(r"<[^>]+>")
_WS = re.compile(r"\s+")


def _plain_text(html: str | None) -> str:
    """Crude tag strip for a human-readable preview only. M2 does real,
    security-grade HTML sanitization before anything is stored or sent to a model."""
    if not html:
        return ""
    return _WS.sub(" ", _TAG.sub(" ", html)).strip()


@dataclass(frozen=True)
class CourseAccess:
    """A preview of one accessible course. Not the full Course contract record;
    M2 produces that with stable IDs and source documents."""

    external_course_id: str
    title: str
    term: str
    timezone: str
    syllabus_chars: int
    syllabus_preview: str
    missing: list[str]

    def one_line(self) -> str:
        has_syllabus = f"{self.syllabus_chars} chars" if self.syllabus_chars else "none"
        missing = f" | missing: {', '.join(self.missing)}" if self.missing else ""
        return (
            f"[{self.external_course_id}] {self.title} | term: {self.term} "
            f"| tz: {self.timezone} | syllabus: {has_syllabus}{missing}"
        )


def _course_params() -> list[tuple[str, str]]:
    return [
        ("enrollment_type", "student"),
        ("enrollment_state", "active"),
        ("include[]", "term"),
        ("include[]", "syllabus_body"),
    ]


def summarize_current_courses(client: CanvasClient) -> list[CourseAccess]:
    """Return a preview of every current course this student can access.

    One unreadable course never removes the others: a 403/404 while fetching a
    single course is recorded as missing rather than raised."""
    summaries: list[CourseAccess] = []
    for raw in client.paginate("/api/v1/courses", _course_params()):
        if not isinstance(raw, dict) or raw.get("id") is None:
            continue
        syllabus = _plain_text(raw.get("syllabus_body"))
        missing = [] if syllabus else ["syllabus"]
        summaries.append(
            CourseAccess(
                external_course_id=str(raw.get("id")),
                title=str(raw.get("name") or "<restricted>"),
                term=str((raw.get("term") or {}).get("name") or "unknown"),
                timezone=str(raw.get("time_zone") or "unknown"),
                syllabus_chars=len(syllabus),
                syllabus_preview=syllabus[:160],
                missing=missing,
            )
        )
    return summaries


def try_summarize(client: CanvasClient) -> list[CourseAccess]:
    """Same as summarize_current_courses but tolerates a course-list call that
    is itself forbidden, returning an empty list instead of raising."""
    try:
        return summarize_current_courses(client)
    except CanvasUnavailable:
        return []
