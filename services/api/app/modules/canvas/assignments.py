"""Read-only fetch of a student's assignments with their own due dates
(owner: Amogh). Part of M2 ingestion. The due date is the student's applicable
date as Canvas returns it for the authenticated student.

Dates are kept exactly as Canvas gives them (ISO, UTC 'Z'); nothing is invented.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .client.http import CanvasClient, CanvasUnavailable

_EXAM = re.compile(r"\b(midterm|final|exam|test)\b", re.I)


@dataclass(frozen=True)
class Assignment:
    external_id: str
    name: str
    due_at: str | None      # ISO timestamp or None (undated)
    points_possible: float | None

    @property
    def looks_like_exam(self) -> bool:
        return bool(_EXAM.search(self.name))


def fetch_assignments(client: CanvasClient, external_course_id: str) -> list[Assignment]:
    """All student-visible assignments for one course. A forbidden course yields
    an empty list rather than failing the whole import."""
    out: list[Assignment] = []
    try:
        for raw in client.paginate(f"/api/v1/courses/{external_course_id}/assignments"):
            if not isinstance(raw, dict) or raw.get("id") is None:
                continue
            out.append(
                Assignment(
                    external_id=str(raw["id"]),
                    name=str(raw.get("name") or ""),
                    due_at=raw.get("due_at") if isinstance(raw.get("due_at"), str) else None,
                    points_possible=(
                        float(raw["points_possible"])
                        if isinstance(raw.get("points_possible"), (int, float))
                        else None
                    ),
                )
            )
    except CanvasUnavailable:
        return []
    return out
