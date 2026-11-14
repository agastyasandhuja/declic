"""Explicit mapping to the feed's consumer-owned VideoReader projection."""

from app.modules.recommendations.models import Playback, VariantCandidate


class FeedVideoReader:
    def __init__(self, service):
        self.service = service

    def _project(self, user_id, video):
        return VariantCandidate.model_validate(
            {
                **video,
                "playback": self.service.playback(user_id, video["video_id"]),
                "thumbnail_url": self.service.storage.signed_url(
                    video["assets"]["thumbnail"]["key"]
                ),
                "captions_ref": self.service.storage.signed_url(video["assets"]["captions"]["key"]),
            }
        )

    def list_variants(self, user_id, objective_ids):
        return [
            self._project(user_id, video)
            for video in self.service.repository.list_videos(user_id, objective_ids)
        ]

    def get_variant(self, user_id, video_id):
        video = self.service.repository.video(video_id, user_id)
        return self._project(user_id, video) if video else None

    def resolve_playback(self, user_id, video_id):
        try:
            return Playback.model_validate(self.service.playback(user_id, video_id))
        except LookupError:
            return None
