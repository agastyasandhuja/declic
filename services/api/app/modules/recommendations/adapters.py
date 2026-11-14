from typing import Protocol

from app.modules.recommendations.models import (
    EntertainmentCandidate,
    ObjectiveCandidate,
    Playback,
    VariantCandidate,
)


class AcademicReader(Protocol):
    def list_objectives(self, user_id: str) -> list[ObjectiveCandidate]: ...


class EntertainmentReader(Protocol):
    def list_candidates(self, user_id: str, limit: int) -> list[EntertainmentCandidate]: ...


class VideoReader(Protocol):
    def list_variants(self, user_id: str, objective_ids: list[str]) -> list[VariantCandidate]: ...

    def get_variant(self, user_id: str, video_id: str) -> VariantCandidate | None: ...

    def resolve_playback(self, user_id: str, video_id: str) -> Playback | None: ...


class EmptyAcademics:
    def list_objectives(self, user_id: str) -> list[ObjectiveCandidate]:
        return []


class EmptyEntertainment:
    def list_candidates(self, user_id: str, limit: int) -> list[EntertainmentCandidate]:
        return []


class EmptyVideos:
    def list_variants(self, user_id: str, objective_ids: list[str]) -> list[VariantCandidate]:
        return []

    def get_variant(self, user_id: str, video_id: str) -> VariantCandidate | None:
        return None

    def resolve_playback(self, user_id: str, video_id: str) -> Playback | None:
        return None
