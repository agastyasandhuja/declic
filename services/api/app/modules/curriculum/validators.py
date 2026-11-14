"""Backend validation of Gemini extraction output (owner: Amogh).

Structured output shapes the JSON; it does not make it correct. This module is
the trust boundary: it rejects/repairs anything the model got wrong before the
data is persisted or handed to Agastya.

Checks: enums, source-id resolvability (drop invented ids), date format and
date/time logic (never a manufactured exam time), and conflicting-date warnings.
Unknown stays null.
"""

from __future__ import annotations

import re
import calendar
from datetime import date as date_cls, datetime, time
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from typing import Any

_EVIDENCE = {"explicit", "inferred", "unknown"}
_KIND = {"midterm", "final", "quiz", "assignment", "other"}
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_TIME_RE = re.compile(r"^\d{2}:\d{2}$")


def _clean_ids(raw: Any, authorized: set[str], warnings: list[str], where: str) -> list[str]:
    ids = [i for i in raw if isinstance(i, str)] if isinstance(raw, list) else []
    kept = [i for i in ids if i in authorized]
    dropped = [i for i in ids if i not in authorized]
    if dropped:
        warnings.append(f"{where}: dropped {len(dropped)} source id(s) not authorized for this user")
    return kept


def _enum(value: Any, allowed: set[str], default: str) -> str:
    return value if isinstance(value, str) and value in allowed else default


def _valid_date(value: Any) -> str | None:
    if not isinstance(value, str) or not _DATE_RE.match(value):
        return None
    try:
        date_cls.fromisoformat(value)
        return value
    except ValueError:
        return None


def _academic_date(raw: dict, timezone: str | None, warnings: list[str], where: str) -> dict:
    """Build a contract AcademicDate, never manufacturing a time from a date."""
    date_value = _valid_date(raw.get("date"))
    time_value = raw.get("time") if isinstance(raw.get("time"), str) and _TIME_RE.match(raw.get("time") or "") else None
    if time_value:
        try:
            time.fromisoformat(time_value)
        except ValueError:
            time_value = None
    evidence = _enum(raw.get("date_evidence"), _EVIDENCE, "unknown")

    if time_value and not date_value:
        warnings.append(f"{where}: a time was given without a valid date; dropping the time")
        time_value = None
    if raw.get("date") and not date_value:
        warnings.append(f"{where}: unparseable date '{raw.get('date')}' treated as unknown")

    if not date_value:
        precision, timestamp = "unknown", None
    elif time_value and timezone:
        precision = "datetime"
        timestamp = datetime.fromisoformat(f"{date_value}T{time_value}").replace(tzinfo=ZoneInfo(timezone)).isoformat()
    else:
        precision, timestamp = "date", None

    return {
        "date": date_value,
        "timestamp": timestamp,
        "timezone": timezone,
        "precision": precision,
        "evidence_status": evidence if date_value else "unknown",
    }


def _ground_date(when, title, excerpts, timezone, warnings):
    """Require a dated row or sentence naming this assessment in a cited excerpt."""
    value = when["date"]
    if not value:
        return when
    if not title.strip():
        return _academic_date({}, timezone, warnings, "")
    day = date_cls.fromisoformat(value)
    month = f"(?:{calendar.month_name[day.month]}|{calendar.month_abbr[day.month]})"
    date_pattern = re.compile(
        rf"(?<![\d/])(?:{value}|{day.month:02d}/{day.day:02d}/{day.year}|"
        rf"{day.month}/{day.day}/{day.year}|{month}\s+0?{day.day},?\s+{day.year})(?![\d/])",
        re.I,
    )
    title_pattern = re.compile(r"(?<!\w)" + re.escape(title.strip()) + r"(?!\w)", re.I)
    evidence_lines = []
    for excerpt in excerpts:
        lines = excerpt.splitlines()
        for index, line in enumerate(lines):
            if not title_pattern.search(line):
                continue
            if line.startswith("Event: ") and index + 1 < len(lines):
                line += " " + lines[index + 1]
            # Stop before the next assessment or sentence whenever possible.
            for match in title_pattern.finditer(line):
                tail = line[match.end():match.end() + 85]
                if re.search(r"\b(?:cancelled|canceled|postponed|no longer|not on|previously|was)\b", tail, re.I):
                    continue
                tail = re.split(r"[;.!?]|\b(?:TBA|TBD|undated)\b", tail, maxsplit=1, flags=re.I)[0]
                if date_pattern.search(tail):
                    evidence_lines.append(tail)
    if not evidence_lines:
        warnings.append("Assessment date could not be verified in its cited evidence")
        return _academic_date({}, timezone, warnings, "")
    # Structured source timestamps already carry their offset. Preserve their
    # precision without trusting the model to reproduce their time or offset.
    for line in evidence_lines:
        match = re.search(r"(?:Scheduled|Due):\s*(" + value +
                          r"T\d{2}:\d{2}:\d{2}(?:Z|[+-]\d{2}:\d{2}))", line)
        if match:
            try:
                exact = datetime.fromisoformat(match[1].replace("Z", "+00:00"))
            except ValueError:
                continue
            localized = exact.astimezone(ZoneInfo(timezone)) if timezone else exact
            when.update(date=localized.date().isoformat(), timestamp=localized.isoformat(),
                        precision="datetime", evidence_status="explicit")
            return when
    if when["timestamp"]:
        clock = when["timestamp"][11:16]
        offset = when["timestamp"][19:]
        if not any(f"T{clock}:00{offset}" in line or
                   (offset == "+00:00" and f"T{clock}:00Z" in line) for line in evidence_lines):
            when.update(timestamp=None, precision="date")
    return when


def validate_extraction(raw: dict, authorized_ids: set[str], *,
                        evidence: dict[str, str] | None = None, source_timezone=None) -> dict:
    """Return a cleaned extraction plus accumulated warnings."""
    warnings: list[str] = list(raw.get("warnings") or []) if isinstance(raw.get("warnings"), list) else []

    title = raw.get("course_title") if isinstance(raw.get("course_title"), str) else ""
    term = raw.get("term") if isinstance(raw.get("term"), str) else None
    timezone = source_timezone or (raw.get("timezone") if isinstance(raw.get("timezone"), str) else None)
    try:
        if timezone:
            ZoneInfo(timezone)
    except (ValueError, ZoneInfoNotFoundError):
        timezone = None

    units = []
    for i, unit in enumerate(raw.get("units") or []):
        if not isinstance(unit, dict):
            continue
        units.append(
            {
                "title": unit.get("title", "") if isinstance(unit.get("title"), str) else "",
                "order": unit.get("order") if isinstance(unit.get("order"), int) else i,
                "objectives": [o for o in (unit.get("objectives") or []) if isinstance(o, str)],
                "source_refs": _clean_ids(unit.get("source_ids"), authorized_ids, warnings, f"unit '{unit.get('title')}'"),
            }
        )

    assessments = []
    seen_dates: dict[str, str | None] = {}
    for assessment in raw.get("assessments") or []:
        if not isinstance(assessment, dict):
            continue
        name = assessment.get("title", "") if isinstance(assessment.get("title"), str) else ""
        when = _academic_date(assessment, timezone, warnings, f"assessment '{name}'")
        refs = _clean_ids(assessment.get("source_ids"), authorized_ids, warnings, f"assessment '{name}'")
        if evidence is not None:
            when = _ground_date(when, name, [evidence[ref] for ref in refs if ref in evidence], timezone, warnings)
        when["source_refs"] = refs if when["date"] else []
        key = re.sub(r"\s+", " ", name).strip().lower()
        if key in seen_dates and seen_dates[key] != when["date"] and when["date"] and seen_dates[key]:
            warnings.append(f"assessment '{name}': conflicting dates {seen_dates[key]} vs {when['date']}")
        seen_dates.setdefault(key, when["date"])
        topics = [t for t in (assessment.get("covered_topics") or []) if isinstance(t, str) and t.strip()]
        scope = _enum(assessment.get("scope_status"), _EVIDENCE, "unknown")
        if evidence is not None:
            # Only retain literal coverage mentioned alongside this assessment in
            # a cited source. Other course material cannot establish exam scope.
            chunks = []
            for ref in refs:
                for line in evidence.get(ref, "").splitlines():
                    for match in re.finditer(r"(?<!\w)" + re.escape(name) + r"(?!\w)", line, re.I) if name else ():
                        tail = line[match.end():match.end() + 300]
                        # Keep only a positive coverage clause. Stop before
                        # contrast, exclusions, or a separate sentence.
                        positive = re.match(
                            r"\s*[:–—-]?\s*(?:covers?|coverage|topics(?: and instructions)?)"
                            r"\s*[:–—-]?\s*(.+)", tail, re.I
                        )
                        if positive:
                            clause = re.split(
                                r"[.;!?]|\b(?:except|excluding|excludes?|but|not|uncovered)\b",
                                positive[1], maxsplit=1, flags=re.I,
                            )[0]
                            chunks.append(clause.casefold())
            topics = [topic for topic in topics if any(
                re.search(r"(?<!\w)" + re.escape(topic.casefold()) + r"(?!\w)", chunk)
                for chunk in chunks
            )]
            if not topics:
                scope = "unknown"
        assessments.append(
            {
                "title": name,
                "kind": _enum(assessment.get("kind"), _KIND, "other"),
                "scheduled": when,
                "scope_status": scope,
                "covered_topics": topics,
                "source_refs": refs,
            }
        )

    textbooks = []
    for book in raw.get("textbooks") or []:
        if not isinstance(book, dict) or not isinstance(book.get("title"), str):
            continue
        textbooks.append(
            {
                "title": book["title"],
                "author": book.get("author") if isinstance(book.get("author"), str) else None,
                "edition": book.get("edition") if isinstance(book.get("edition"), str) else None,
                "isbn": book.get("isbn") if isinstance(book.get("isbn"), str) else None,
                "source_refs": _clean_ids(book.get("source_ids"), authorized_ids, warnings, f"textbook '{book['title']}'"),
            }
        )

    # Duplicate mentions of one named assessment share a stable correction ID.
    # Conflicting dates remain visible via the warning and require review.
    unique_assessments = {}
    for item in assessments:
        key = " ".join(item["title"].casefold().split())
        existing = unique_assessments.get(key)
        if existing is None:
            unique_assessments[key] = item
            continue
        existing["source_refs"] = list(dict.fromkeys(existing["source_refs"] + item["source_refs"]))
        dates = {existing["scheduled"]["date"], item["scheduled"]["date"]} - {None}
        if len(dates) > 1:
            existing["scheduled"] = _academic_date({}, timezone, warnings, "")
            existing["scheduled"]["source_refs"] = []
            existing["date_conflict"] = True
        elif not existing.get("date_conflict") and not existing["scheduled"]["date"]:
            existing["scheduled"] = item["scheduled"]

    return {
        "course_title": title,
        "term": term,
        "timezone": timezone,
        "units": units,
        "assessments": list(unique_assessments.values()),
        "textbooks": textbooks,
        "warnings": warnings,
    }
