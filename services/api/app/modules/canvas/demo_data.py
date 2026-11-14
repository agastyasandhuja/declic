"""A built-in, clearly-synthetic Canvas stand-in.

Lets `validate_access --demo` show what a real run looks like before any token
exists. This is NOT UMass data and must never be presented as a live sync.
"""

from __future__ import annotations

import json

from .client.http import Response

_SELF = {"id": 900001, "name": "Demo Student (synthetic)"}

_COURSES = [
    {
        "id": 101,
        "name": "COMPSCI 187 Data Structures (SYNTHETIC)",
        "time_zone": "America/New_York",
        "term": {"name": "Fall 2026 (synthetic)"},
        "syllabus_body": "<p>Units: arrays, <b>linked lists</b>, stacks, trees. "
        "Midterm 2 covers linked lists and recursion.</p>",
    },
    {
        "id": 102,
        "name": "STATISTC 240 Intro to Probability (SYNTHETIC)",
        "time_zone": "America/New_York",
        "term": {"name": "Fall 2026 (synthetic)"},
        "syllabus_body": "<p>Counting, conditional probability, random variables, "
        "expectation. Final is cumulative.</p>",
    },
    {
        "id": 103,
        "name": "ACCOUNTG 221 Principles of Accounting (SYNTHETIC)",
        "time_zone": "America/New_York",
        "term": {"name": "Fall 2026 (synthetic)"},
        "syllabus_body": None,  # a course with no syllabus posted yet
    },
]


def demo_transport(url, headers, timeout):  # signature matches client.http.Transport
    if url.endswith("/api/v1/users/self"):
        return Response(200, {}, json.dumps(_SELF).encode())
    if "/api/v1/courses" in url:
        return Response(200, {}, json.dumps(_COURSES).encode())
    return Response(404, {}, b"{}")
