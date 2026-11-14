"""Conservative teaching-evidence gate; schedule evidence is never lesson content."""

import re
from dataclasses import asdict, is_dataclass

_ADMIN = re.compile(
    r"\b(?:due\s+(?:date|by|on|tomorrow|today|tonight|next|this|Monday|Tuesday|Wednesday|"
    r"Thursday|Friday|Saturday|Sunday|January|February|March|April|May|June|July|August|"
    r"September|October|November|December)|deadline|submit|submission|homework|smartbook|"
    r"assignments?\s+(?:instructions?|deadlines?|due)|"
    r"is an assignment(?! operator| expression| statement)|"
    r"syllabus|grading|grades?|office hours|attendance|late work|course policy|"
    r"click|log ?in|sign ?in|instructor|teaching assistant|canvas|points possible)\b",
    re.I,
)
_PLACEHOLDER = re.compile(
    r"\b(?:(?:insufficient|unavailable) (?:course |source |conceptual |instructional |teaching )?"
    r"(?:material|content|evidence|information)|(?:material|content|evidence) "
    r"(?:unavailable|not provided)|"
    r"no (?:accessible |supported )?(?:course|source|conceptual|instructional|teaching) "
    r"(?:material|content|information))\b",
    re.I,
)
_ASSESSMENT_TITLE = re.compile(
    r"\b(?:exam|midterm|quiz|homework|assignment(?! operators?\b| expressions?\b| statements?\b)|"
    r"worked solutions?|answer key)\b",
    re.I,
)
_NON_TEACHING_KINDS = {"assignment", "calendar_event", "module", "canvas_course", "syllabus"}


class InsufficientTeachingEvidence(ValueError):
    """A normal unavailable result, never a reason to invent textbook content."""


def source_dict(source):
    return asdict(source) if is_dataclass(source) else source


def teaching_resource(source):
    source = source_dict(source)
    return source.get("resource_type") not in _NON_TEACHING_KINDS and not _ASSESSMENT_TITLE.search(
        source.get("title", "")
    )


def teaching_text(source):
    """Drop administrative resources/lines before either model sees an excerpt.

    This is an evidence floor, not a claim of semantic entailment. The grounding
    prompt must still restrict each fact to the retained source text.
    """
    source = source_dict(source)
    if not teaching_resource(source):
        return ""
    text = source.get("text") or ""
    statements = [
        part.strip()
        for part in re.split(r"(?<=[.!?])\s+|\n+", text)
        if len(part.strip()) >= 35 and not _ADMIN.search(part) and not _PLACEHOLDER.search(part)
    ]
    retained = "\n".join(statements)
    return retained if len(retained) >= 45 and len(retained.split()) >= 8 else ""


def teaching_sources(sources):
    result = []
    for source in sources:
        text = teaching_text(source)
        if text:
            result.append({**source_dict(source), "text": text})
    return result


def validate_teaching_lesson(lesson):
    """Reject unsupported placeholders and administrative facts before publication."""
    title = lesson.get("title", "")
    facts = lesson.get("facts", [])
    if (
        not title.strip()
        or _PLACEHOLDER.search(title)
        or _ADMIN.search(title)
        or len(facts) < 2
        or any(
            not fact.strip() or _ADMIN.search(fact) or _PLACEHOLDER.search(fact) for fact in facts
        )
    ):
        raise InsufficientTeachingEvidence("Sources do not support a conceptual lesson")


def matching_teaching_refs(topic, units, sources):
    """Use exact unit membership or conservative chapter/title overlap, not a guess."""
    eligible = {source["source_id"]: source for source in teaching_sources(sources)}
    folded = " ".join(topic.casefold().split())
    refs = []
    for unit in units:
        titles = [unit.get("title", ""), *unit.get("objectives", [])]
        if any(" ".join(title.casefold().split()) == folded for title in titles):
            refs.extend(ref for ref in unit.get("source_refs", []) if ref in eligible)
    chapter = re.search(r"\b(?:ch(?:apter)?\.?)[\s_-]*(\d+)\b", topic, re.I)
    tokens = set(re.findall(r"[a-z]{4,}", folded)) - {
        "chapter",
        "review",
        "practice",
        "homework",
        "assignment",
        "smartbook",
        "lecture",
    }
    for ref, source in eligible.items():
        title = source.get("title", "").casefold()
        title_chapter = re.search(r"\b(?:ch(?:apter)?\.?)[\s_-]*(\d+)\b", title, re.I)
        if chapter and title_chapter and chapter.group(1) == title_chapter.group(1):
            refs.append(ref)
        elif tokens and len(tokens & set(re.findall(r"[a-z]{4,}", title))) >= min(2, len(tokens)):
            refs.append(ref)
    return list(dict.fromkeys(refs))
