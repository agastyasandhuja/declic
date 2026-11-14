"""JSON schemas and record shapes for the curriculum pipeline (owner: Amogh).

EXTRACTION_SCHEMA is what we ask Gemini to return for one course. It is a
constrained OpenAPI-subset schema (Gemini structured output). The backend still
validates the result afterwards — a schema shapes output, it does not make it true.

The assembled AcademicProfile follows contracts/academics.md.
"""

from __future__ import annotations

SCHEMA_VERSION = "1"

_EVIDENCE = ["explicit", "inferred", "unknown"]
_ASSESSMENT_KIND = ["midterm", "final", "quiz", "assignment", "other"]

EXTRACTION_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "course_title": {"type": "string"},
        "term": {"type": "string", "nullable": True},
        "timezone": {
            "type": "string",
            "nullable": True,
            "description": "IANA timezone such as America/New_York, or null if unknown",
        },
        "units": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "order": {"type": "integer"},
                    "objectives": {"type": "array", "items": {"type": "string"}},
                    "source_ids": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["title", "order", "objectives", "source_ids"],
            },
        },
        "assessments": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "kind": {"type": "string", "enum": _ASSESSMENT_KIND},
                    "date": {
                        "type": "string",
                        "nullable": True,
                        "description": "YYYY-MM-DD, or null if no date is stated",
                    },
                    "time": {
                        "type": "string",
                        "nullable": True,
                        "description": "HH:MM 24h, or null. Never invent a time.",
                    },
                    "date_evidence": {"type": "string", "enum": _EVIDENCE},
                    "scope_status": {"type": "string", "enum": _EVIDENCE},
                    "covered_topics": {"type": "array", "items": {"type": "string"}},
                    "source_ids": {"type": "array", "items": {"type": "string"}},
                },
                "required": [
                    "title", "kind", "date", "time",
                    "date_evidence", "scope_status", "covered_topics", "source_ids",
                ],
            },
        },
        "textbooks": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "author": {"type": "string", "nullable": True},
                    "edition": {"type": "string", "nullable": True},
                    "isbn": {"type": "string", "nullable": True},
                    "source_ids": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["title", "author", "edition", "isbn", "source_ids"],
            },
        },
        "warnings": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["course_title", "term", "timezone", "units", "assessments", "textbooks", "warnings"],
}
