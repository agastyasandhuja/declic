"""Real-time course urgency from actual Canvas due dates (owner: Amogh).

Deterministic: given the student's real assignments and the real current time,
it computes which graded work is upcoming vs past and how soon the next item is.
This drives curriculum prioritization (which courses/topics to teach first).
Agastya owns the final runtime feed ranking; this provides the evidence for it.

No dates are invented. An undated item (e.g. a Canvas "Midterm 1" with no due
date) is reported as undated, never guessed.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from ..canvas.assignments import Assignment


def _parse(ts: str | None) -> datetime | None:
    if not isinstance(ts, str) or not ts:
        return None
    try:
        value = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return value if value.utcoffset() is not None else None
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
        lines.append(f"  - {a.name} | Due: {due.isoformat()} ({when})")
    undated_exams = [a.name for a in assignments if a.looks_like_exam and not a.due_at]
    if undated_exams:
        lines.append("Exams listed without a date in Canvas (do not guess a date): "
                     + ", ".join(undated_exams))
    return "\n".join(lines)


def upcoming_assessments(assessments, now, course_timezone=None):
    """Return verified future targets, with exams ahead of ordinary graded work."""
    targets = []
    for assessment in assessments:
        scheduled = assessment.get("scheduled", {})
        if (assessment.get("date_conflict") or scheduled.get("evidence_status")
                not in {"explicit", "user_confirmed"}):
            continue
        if scheduled.get("precision") == "datetime":
            deadline = _parse(scheduled.get("timestamp"))
            if deadline is None or deadline.utcoffset() is None or deadline <= now:
                continue
        elif scheduled.get("precision") == "date":
            try:
                zone = ZoneInfo(scheduled.get("timezone") or course_timezone or "")
                day = date.fromisoformat(scheduled["date"])
                if day < now.astimezone(zone).date():
                    continue
                # Sort at the end of the local day without exposing a fabricated timestamp.
                deadline = datetime.combine(day + timedelta(days=1), time.min, zone)
            except (KeyError, TypeError, ValueError, OverflowError, ZoneInfoNotFoundError):
                continue
        else:
            continue
        exam = assessment["kind"] in {"midterm", "final"} or assessment.get("is_exam") is True
        targets.append((not exam, deadline, assessment["assessment_id"], assessment))
    return [target[-1] for target in sorted(targets, key=lambda target: target[:3])]


_WORK_PREFIX = re.compile(
    r"^(?:(?:problem set|programming assignment|assignment|homework|challenge|discussion|"
    r"exercise|project|quiz|lab|hw|pa|ps)(?=\W|\d|$)\s*(?:#?\s*\d+(?:[.\-]\d+)*)?\b[\s:–—.-]*)",
    re.I,
)
_ADMINISTRATIVE = re.compile(
    r"\b(?:acknowledg(?:e)?ments?|collaboration policy|course evaluations?|"
    r"attendance|submission instructions|syllabus quiz|starter project)\b",
    re.I,
)
_GENERIC = re.compile(
    r"^(?:(?:core|key|foundational)\s+)?(?:concepts?|principles?|topics?|"
    r"exercises?|practice|problems?|review|welcome|introduction|discussion|"
    r"assignments?|homework|quiz|lab|project|exam|midterm|final|\d+)(?:\s+\d+)?$",
    re.I,
)


def assessment_topics(target):
    """Return only specific, directly supported topics for this exact assessment."""
    title = target["title"].strip()
    # Canvas titles sometimes start with an icon or variation selector.
    title = title.lstrip("".join(char for char in title[:12]
                                 if unicodedata.category(char) in {"So", "Mn", "Cf"} or char.isspace()))
    if _ADMINISTRATIVE.search(title):
        return []
    topics = []
    if target.get("scope_status") in {"explicit", "user_confirmed"}:
        topics.extend(target.get("covered_topics", []))
    is_exam = target["kind"] in {"midterm", "final"} or target.get("is_exam")
    if not is_exam and target["kind"] in {"assignment", "quiz"}:
        match = _WORK_PREFIX.match(title)
        topic = title[match.end():] if match else title
        if not re.match(r"^(?:chapter|section|unit|module|week)\s*#?\d", topic, re.I):
            topics.append(topic)
    unique = {}
    for topic in topics:
        value = topic.strip()
        if any(char.isalpha() for char in value) and not _GENERIC.fullmatch(value):
            unique.setdefault(" ".join(value.casefold().split()), value)
    return list(unique.values())


def priority_targets(assessments, now, course_timezone=None):
    """Prefer the next exam with verified scope, then the nearest topical coursework."""
    upcoming = upcoming_assessments(assessments, now, course_timezone)
    exams = [item for item in upcoming if item["kind"] in {"midterm", "final"} or item.get("is_exam")]
    coursework = [item for item in upcoming if item not in exams and assessment_topics(item)]
    if exams and assessment_topics(exams[0]):
        # Keep earlier coursework eligible while giving the next exam first priority.
        exam_day = exams[0]["scheduled"]["date"]
        earlier = [item for item in coursework if item["scheduled"]["date"] <= exam_day]
        return [exams[0], *earlier[:4]]
    return coursework[:5]


def target_topic_is_supported(topic, target):
    """Revalidate a saved topic against the current assessment evidence."""
    key = " ".join(topic.casefold().split())
    return key in {" ".join(value.casefold().split()) for value in assessment_topics(target)}
