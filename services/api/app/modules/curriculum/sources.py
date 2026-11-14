"""Scoped source resolution (owner: Amogh).

Turns a user's stored SourceDocuments into bounded, authorized excerpts that can
be shown to Gemini. Everything is user-scoped: a resolver built for one user can
only ever read that user's sources. Gemini receives excerpts plus their source
IDs, never storage paths, tokens or the raw file bytes.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from ..canvas.client.http import CanvasClient
from ..canvas.courses import fetch_course_syllabi
from ..canvas.ingestion.uploads import load_sources, read_text

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

    @property
    def has_text(self) -> bool:
        return bool(self.text and self.text.strip())


class Resolver(Protocol):
    """What the Gemini pipeline needs from any source provider (Canvas or upload)."""

    def list_sources(self) -> list[ResolvedSource]: ...
    def sources_for_course(self, course_id: str) -> list[ResolvedSource]: ...
    def course_ids(self) -> list[str]: ...


class CanvasSourceResolver:
    """PRIMARY M3 path: reads the signed-in student's live Canvas courses and
    their syllabi through the authorized read-only client. No manual upload.

    Each course's syllabus becomes one authorized source with a stable id.
    Courses without a syllabus yield a source with text=None (recorded as
    needing more material; M2 adds modules/pages/files/assignments)."""

    def __init__(self, client: CanvasClient) -> None:
        self._client = client
        self._cache: list[ResolvedSource] | None = None

    def _load(self) -> list[ResolvedSource]:
        if self._cache is None:
            sources: list[ResolvedSource] = []
            for course_id, name, text in fetch_course_syllabi(self._client):
                if text and len(text) > MAX_EXCERPT_CHARS:
                    text = text[:MAX_EXCERPT_CHARS]
                sources.append(
                    ResolvedSource(
                        source_id=f"src_canvas_{course_id}_syllabus",
                        course_id=course_id,
                        title=f"{name} — syllabus",
                        resource_type="canvas_syllabus",
                        provenance_mode="canvas",
                        text=text,
                    )
                )
            self._cache = sources
        return self._cache

    def list_sources(self) -> list[ResolvedSource]:
        return self._load()

    def sources_for_course(self, course_id: str) -> list[ResolvedSource]:
        return [s for s in self._load() if s.course_id == course_id]

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
        self._user_id = user_id
        self._storage_dir = storage_dir

    def list_sources(self) -> list[ResolvedSource]:
        resolved: list[ResolvedSource] = []
        for record in load_sources(self._user_id, self._storage_dir):
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
