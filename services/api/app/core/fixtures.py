"""Explicit synthetic catalog. URLs are non-playable metadata test placeholders."""

import json
from pathlib import Path

from app.modules.quizzes.schemas import QuizDefinition
from app.modules.recommendations.models import (
    EntertainmentCandidate,
    ObjectiveCandidate,
    VariantCandidate,
)


class FixtureCatalog:
    def __init__(self, path: Path | None = None):
        path = path or Path(__file__).resolve().parents[4] / "fixtures/feed/api-catalog.json"
        data = json.loads(path.read_text())
        self.objectives = [ObjectiveCandidate.model_validate(o) for o in data["objectives"]]
        self.variants = [VariantCandidate.model_validate(v) for v in data["variants"]]
        self.clips = [EntertainmentCandidate.model_validate(v) for v in data["entertainment"]]
        self.definitions = [QuizDefinition.model_validate(q) for q in data["quizzes"]]

    def list_objectives(self, user_id):
        return [o for o in self.objectives if o.user_id == user_id]

    def list_candidates(self, user_id, limit):
        return self.clips[:limit]

    def list_variants(self, user_id, objective_ids):
        return [
            v
            for v in self.variants
            if v.objective_id in objective_ids
            and (v.scope == "shared_generic" or v.owner_user_id == user_id)
        ]

    def get_variant(self, user_id, video_id):
        return next(
            (
                v
                for v in self.variants
                if v.video_id == video_id
                and (v.scope == "shared_generic" or v.owner_user_id == user_id)
            ),
            None,
        )

    def resolve_playback(self, user_id, video_id):
        video = self.get_variant(user_id, video_id)
        return video.playback if video else None

    def list_for_objective(self, user_id, objective_id):
        return [
            q
            for q in self.definitions
            if objective_id in q.objective_ids
            and (q.scope == "shared_generic" or q.owner_user_id == user_id)
        ]
