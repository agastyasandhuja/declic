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
from datetime import date as date_cls
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
    evidence = _enum(raw.get("date_evidence"), _EVIDENCE, "unknown")

    if time_value and not date_value:
        warnings.append(f"{where}: a time was given without a valid date; dropping the time")
        time_value = None
    if raw.get("date") and not date_value:
        warnings.append(f"{where}: unparseable date '{raw.get('date')}' treated as unknown")

    if not date_value:
        precision, timestamp = "unknown", None
    elif time_value:
        precision, timestamp = "datetime", f"{date_value}T{time_value}:00"
    else:
        precision, timestamp = "date", None

    return {
        "date": date_value,
        "timestamp": timestamp,
        "timezone": timezone,
        "precision": precision,
        "evidence_status": evidence if date_value else ("unknown" if not date_value else evidence),
    }


def validate_extraction(raw: dict, authorized_ids: set[str]) -> dict:
    """Return a cleaned extraction plus accumulated warnings."""
    warnings: list[str] = list(raw.get("warnings") or []) if isinstance(raw.get("warnings"), list) else []

    title = raw.get("course_title") if isinstance(raw.get("course_title"), str) else ""
    term = raw.get("term") if isinstance(raw.get("term"), str) else None
    timezone = raw.get("timezone") if isinstance(raw.get("timezone"), str) else None

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
        key = re.sub(r"\s+", " ", name).strip().lower()
        if key in seen_dates and seen_dates[key] != when["date"] and when["date"] and seen_dates[key]:
            warnings.append(f"assessment '{name}': conflicting dates {seen_dates[key]} vs {when['date']}")
        seen_dates.setdefault(key, when["date"])
        assessments.append(
            {
                "title": name,
                "kind": _enum(assessment.get("kind"), _KIND, "other"),
                "scheduled": when,
                "scope_status": _enum(assessment.get("scope_status"), _EVIDENCE, "unknown"),
                "covered_topics": [t for t in (assessment.get("covered_topics") or []) if isinstance(t, str)],
                "source_refs": _clean_ids(assessment.get("source_ids"), authorized_ids, warnings, f"assessment '{name}'"),
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

    return {
        "course_title": title,
        "term": term,
        "timezone": timezone,
        "units": units,
        "assessments": assessments,
        "textbooks": textbooks,
        "warnings": warnings,
    }
