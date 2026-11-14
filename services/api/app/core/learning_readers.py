"""Map reusable private topic assets back to the student's academic objective."""

from app.core import collections as tables
from app.modules.videos.adapters import FeedVideoReader


class BoundVideoReader(FeedVideoReader):
    def __init__(self, service, database):
        super().__init__(service)
        self.database = database

    def _binding_query(self, user_id):
        query = {"user_id": user_id}
        if self.database.mongo is not None:
            profile = self.database.mongo.academic_profiles.find_one(
                {"user_id": user_id}, {"revision": 1}
            )
            if profile:
                query["profile_revision"] = profile["revision"]
        return query

    def list_variants(self, user_id, objective_ids):
        bindings = self.database.read(
            lambda tx: tx.find(
                tables.bindings,
                {**self._binding_query(user_id), "objective_id": {"$in": objective_ids[:200]}},
            )
        )
        originals = {row["objective_id"]: row["topic_id"] for row in bindings}
        videos = self.service.repository.list_videos(user_id, list(set(originals.values())))
        signed = self._sign_owned(videos) if videos else {}
        return [
            self._project(user_id, {**video, "objective_id": objective}, signed)
            for objective, topic in originals.items()
            for video in videos
            if video["objective_id"] == topic
        ]

    def get_variant_for_objective(self, user_id, video_id, objective_id):
        binding = self.database.read(
            lambda tx: tx.find_one(
                tables.bindings, {**self._binding_query(user_id), "objective_id": objective_id}
            )
        )
        video = self.service.repository.video(video_id, user_id)
        if not binding or not video or binding["topic_id"] != video["objective_id"]:
            return None
        return self._project(
            user_id, {**video, "objective_id": objective_id}, self._sign_owned([video])
        )
