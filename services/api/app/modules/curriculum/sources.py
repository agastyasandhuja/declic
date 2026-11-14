"""Scoped source resolution (owner: Amogh).

Turns a user's stored SourceDocuments into bounded, authorized excerpts that can
be shown to Gemini. Everything is user-scoped: a resolver built for one user can
only ever read that user's sources. Gemini receives excerpts plus their source
IDs, plus selected inline media through the owner-scoped reader.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Protocol
from xml.etree import ElementTree
from zipfile import BadZipFile

from ..canvas.assignments import Assignment, fetch_assignments
from ..canvas.client.http import CanvasAuthError, CanvasClient, CanvasError
from ..canvas.courses import fetch_current_courses
from ..canvas.ingestion.resources import FILE_MEDIA, MAX_FILE_BYTES, _file_text, fetch_resources, parse_html
from xml.etree import ElementTree
from zipfile import BadZipFile
from ..canvas.ingestion.uploads import load_sources, read_text
from .timing import schedule_text

# Keep each excerpt bounded so one large file cannot dominate a prompt.
MAX_EXCERPT_CHARS = 12000


@dataclass(frozen=True)
class ResolvedSource:
    source_id: str
    course_id: str
    title: str
    resource_type: str
    provenance_mode: str
    text: str | None  # None when the format cannot be extracted yet

    external_id: str | None = None
    source_updated_at: str | None = None
    fetched_at: str | None = None
    locator: str = "whole source"
    content_hash: str | None = None

    @property
    def has_text(self) -> bool:
        return bool(self.text and self.text.strip())


class Resolver(Protocol):
    """What the Gemini pipeline needs from any source provider (Canvas or upload)."""

    def list_sources(self) -> list[ResolvedSource]: ...
    def sources_for_course(self, course_id: str) -> list[ResolvedSource]: ...
    def course_ids(self) -> list[str]: ...


class CanvasSourceResolver:
    """Snapshot of student-visible sources from an already authorized Canvas client."""

    # Learning Resource Center tutoring sections duplicate a real enrolled course
    # and carry no graded work; skip them so one class is not counted twice.
    _SKIP = re.compile(r"\bLRC\b", re.I)

    def __init__(
        self, client: CanvasClient, *, owner_user_id: str | None = None,
        with_assignments: bool = True, skip_tutoring: bool = True
    ) -> None:
        self._client = client
        self.owner_user_id = owner_user_id
        self._with_assignments = with_assignments
        self._skip_tutoring = skip_tutoring
        self._cache: list[ResolvedSource] | None = None
        self._course_info: dict[str, dict] = {}
        self._file_urls: dict[tuple[str, str], str] = {}
        self._selected: dict[str, list[str]] = {}
        self._opened: dict[tuple[str, str], ResolvedSource] = {}
        self._assignments: dict[str, list[Assignment]] = {}

    def _load(self) -> list[ResolvedSource]:
        if self._cache is None:
            sources: list[ResolvedSource] = []
            for row in fetch_current_courses(self._client):
                course_id, name = str(row["id"]), str(row.get("name") or "")
                if self._skip_tutoring and self._SKIP.search(name):
                    continue
                fetched_at = datetime.now(timezone.utc).isoformat()
                syllabus, files = parse_html(row.get("syllabus_body"))
                missing = [] if syllabus else ["syllabus"]
                parts = [f"SYLLABUS:\n{syllabus}"] if syllabus else []
                if self._with_assignments:
                    try:
                        assignments = fetch_assignments(self._client, course_id)
                    except CanvasAuthError:
                        raise
                    except CanvasError:
                        assignments = []
                        missing.append("assignments: unavailable")
                    self._assignments[course_id] = assignments
                    if assignments:
                        parts.append(schedule_text(assignments))
                excerpt = "\n\n".join(parts)
                sources.append(ResolvedSource(
                    f"src_canvas_{course_id}_overview", course_id, name, "canvas_course",
                    "canvas", excerpt[:MAX_EXCERPT_CHARS] or None, course_id,
                    row.get("updated_at"), fetched_at, "syllabus and assignments",
                    hashlib.sha256(excerpt.encode()).hexdigest(),
                ))

                for assignment in self._assignments.get(course_id, []):
                    description, attachments = parse_html(assignment.description)
                    files.update(attachments)
                    key = f"{course_id}:assignment:{assignment.external_id}"
                    title = assignment.name
                    text = f"{title} | Due: {assignment.due_at or 'undated'}"
                    if description:
                        text += f"\n{title} topics and instructions: {description}"
                    sources.append(ResolvedSource(
                        "src_canvas_" + hashlib.sha256(key.encode()).hexdigest()[:24],
                        course_id, title, "assignment", "canvas", text[:MAX_EXCERPT_CHARS],
                        assignment.external_id, fetched_at=fetched_at, locator="assignment description",
                    ))
                resources, unavailable = fetch_resources(self._client, course_id, files)
                resources.sort(key=lambda resource: resource.kind != "calendar_event")
                for resource in resources:
                    key = f"{course_id}:{resource.kind}:{resource.external_id}"
                    content = resource.text or ""
                    source_id = "src_canvas_" + hashlib.sha256(key.encode()).hexdigest()[:24]
                    if resource.download_url:
                        self._file_urls[course_id, source_id] = resource.download_url
                    sources.append(ResolvedSource(
                        source_id, course_id, resource.title, resource.kind, "canvas",
                        content[:MAX_EXCERPT_CHARS] or None, resource.external_id,
                        resource.updated_at, fetched_at, resource.locator,
                        resource.content_hash or (hashlib.sha256(content.encode()).hexdigest() if content else None),
                    ))
                self._course_info[course_id] = dict(
                    title=name, external_course_id=course_id, timezone=row.get("time_zone"),
                    term=(row.get("term") or {}).get("name"), missing_sources=missing + unavailable,
                )
            self._cache = sources
        return self._cache

    def course_info(self, course_id: str) -> dict:
        self._load()
        return self._course_info[course_id]

    def assignments_for_course(self, course_id: str) -> list[Assignment]:
        self._load()
        return self._assignments.get(course_id, [])

    def remember_selected_sources(self, course_id, source_ids):
        self._selected[course_id] = list(source_ids)

    def sources_for_planning(self, course_id):
        sources = self.sources_for_course(course_id)
        indexed = {source.source_id: source for source in sources}
        preferred = [indexed[key] for key in self._selected.get(course_id, []) if key in indexed]
        chosen = {source.source_id for source in preferred}
        return preferred + [source for source in sources if source.source_id not in chosen]

    def can_open_file(self, course_id, source_id):
        return (course_id, source_id) in self._file_urls

    def open_file(self, course_id, source):
        """Resolve only same-course entries from the private Canvas inventory."""
        key = course_id, source.source_id
        url = self._file_urls.get(key)
        if source.course_id != course_id or not url:
            return source, None
        try:
            data = self._client.download(url, MAX_FILE_BYTES)
            suffix = PurePosixPath(source.title).suffix.lower()
            media_type, magic = FILE_MEDIA.get(suffix, (None, b""))
            inline = (media_type, data) if media_type and data.startswith(magic) else None
            text = _file_text(suffix, data)
        except CanvasAuthError:
            raise
        except (CanvasError, UnicodeError, BadZipFile, ElementTree.ParseError, RuntimeError):
            return source, None
        resolved = replace(source, text=text[:MAX_EXCERPT_CHARS] if text else None,
                           content_hash=hashlib.sha256(data).hexdigest())
        self._opened[key] = resolved
        return resolved, inline

    def list_sources(self) -> list[ResolvedSource]:
        return [self._opened.get((s.course_id, s.source_id), s) for s in self._load()]

    def sources_for_course(self, course_id: str) -> list[ResolvedSource]:
        return [s for s in self.list_sources() if s.course_id == course_id]

    def course_ids(self) -> list[str]:
        seen: list[str] = []
        for source in self._load():
            if source.course_id not in seen:
                seen.append(source.course_id)
        return seen


class SourceResolver:
    """FALLBACK path: reads one user's uploaded sources from the private upload
    store, for when live Canvas access is unavailable."""

    def __init__(self, user_id: str, storage_dir: Path) -> None:
        if not user_id:
            raise ValueError("a user id is required to resolve sources")
        self.owner_user_id = user_id
        self._storage_dir = storage_dir

    def list_sources(self) -> list[ResolvedSource]:
        resolved: list[ResolvedSource] = []
        for record in load_sources(self.owner_user_id, self._storage_dir):
            text = read_text(record, self._storage_dir)
            if text and len(text) > MAX_EXCERPT_CHARS:
                text = text[:MAX_EXCERPT_CHARS]
            resolved.append(
                ResolvedSource(
                    source_id=record["source_id"],
                    course_id=record["course_id"],
                    title=record.get("title", ""),
                    resource_type=record.get("resource_type", "unknown"),
                    provenance_mode=(record.get("provenance") or {}).get("mode", "unknown"),
                    text=text,
                    external_id=record.get("external_id"),
                    source_updated_at=record.get("source_updated_at"),
                    fetched_at=record.get("fetched_at"),
                    content_hash=record.get("content_hash"),
                )
            )
        return resolved

    def sources_for_course(self, course_id: str) -> list[ResolvedSource]:
        return [s for s in self.list_sources() if s.course_id == course_id]

    def course_ids(self) -> list[str]:
        seen: list[str] = []
        for source in self.list_sources():
            if source.course_id not in seen:
                seen.append(source.course_id)
        return seen


def select_excerpts(sources: list[ResolvedSource], budget: int) -> list[ResolvedSource]:
    """Bound aggregate size and distribute space across source kinds."""
    groups = {}
    for source in sources:
        if source.has_text:
            groups.setdefault(source.resource_type, []).append(source)
    selected = []
    per_kind = budget // max(1, len(groups))
    for group in groups.values():
        for source in group[:12]:
            limit = min(MAX_EXCERPT_CHARS, per_kind // min(len(group), 12))
            selected.append(replace(source, title=source.title[:200], text=source.text[:limit]))
    return selected
