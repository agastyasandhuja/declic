"""Real-time course urgency from actual Canvas due dates (owner: Amogh).

Deterministic: given the student's real assignments and the real current time,
it computes which graded work is upcoming vs past and how soon the next item is.
This drives curriculum prioritization (which courses/topics to teach first).
Agastya owns the final runtime feed ranking; this provides the evidence for it.

No dates are invented. An undated item (e.g. a Canvas "Midterm 1" with no due
date) is reported as undated, never guessed.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from ..canvas.assignments import Assignment


def _parse(ts: str | None) -> datetime | None:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return None


@dataclass(frozen=True)
class DueItem:
    name: str
    due_at: datetime
    days_until: int
    is_exam: bool


@dataclass(frozen=True)
class CourseTiming:
    next_due_name: str | None
    next_due_date: str | None       # YYYY-MM-DD or None
    days_until_next: int | None
    upcoming_count: int
    upcoming: list[DueItem]
    has_undated_exam: bool          # an exam exists but Canvas gives no date
    next_exam_days: int | None      # days to next dated exam, if any

    @property
    def urgency(self) -> float:
        """0..1; higher = more urgent. Soonest upcoming item dominates.
        A course with no upcoming dated work scores 0."""
        if self.days_until_next is None:
            return 0.0
        # within a week ~> near 1.0, decaying over ~6 weeks
        return round(max(0.0, min(1.0, 1.0 - self.days_until_next / 42.0)), 3)


def course_timing(assignments: list[Assignment], now: datetime | None = None) -> CourseTiming:
    now = now or datetime.now(timezone.utc)
    upcoming: list[DueItem] = []
    next_exam_days: int | None = None
    for a in assignments:
        due = _parse(a.due_at)
        if due is None:
            continue
        days = (due - now).days
        if due >= now:
            item = DueItem(a.name, due, days, a.looks_like_exam)
            upcoming.append(item)
            if a.looks_like_exam and (next_exam_days is None or days < next_exam_days):
                next_exam_days = days
    upcoming.sort(key=lambda i: i.due_at)
    has_undated_exam = any(a.looks_like_exam and not a.due_at for a in assignments)

    if upcoming:
        nxt = upcoming[0]
        return CourseTiming(
            next_due_name=nxt.name,
            next_due_date=nxt.due_at.date().isoformat(),
            days_until_next=nxt.days_until,
            upcoming_count=len(upcoming),
            upcoming=upcoming[:8],
            has_undated_exam=has_undated_exam,
            next_exam_days=next_exam_days,
        )
    return CourseTiming(None, None, None, 0, [], has_undated_exam, None)


def schedule_text(assignments: list[Assignment], now: datetime | None = None) -> str:
    """A compact, real schedule summary to give Gemini topic + timing context.
    Only real names and real dates; undated items are labelled undated."""
    now = now or datetime.now(timezone.utc)
    lines = [f"Course graded work (student's own due dates), as of {now.date().isoformat()}:"]
    dated = sorted((a for a in assignments if _parse(a.due_at)), key=lambda a: _parse(a.due_at))
    for a in dated[-25:]:  # recent + upcoming window
        due = _parse(a.due_at)
        when = "upcoming" if due >= now else "past"
        lines.append(f"  - {due.date().isoformat()} ({when}): {a.name}")
    undated_exams = [a.name for a in assignments if a.looks_like_exam and not a.due_at]
    if undated_exams:
        lines.append("Exams listed without a date in Canvas (do not guess a date): "
                     + ", ".join(undated_exams))
    return "\n".join(lines)
