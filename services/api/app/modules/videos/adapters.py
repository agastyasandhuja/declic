"""Explicit mapping to the feed's consumer-owned VideoReader projection."""

from datetime import UTC, datetime, timedelta

from app.modules.recommendations.models import Playback, VariantCandidate


class FeedVideoReader:
    def __init__(self, service):
        self.service = service

    def _sign_owned(self, videos):
        # Call only after the repository's owner-filtered query. Reused topic
        # bindings share physical assets; do not sign those paths repeatedly.
        keys = list(dict.fromkeys(
            video["assets"][kind]["key"]
            for video in videos
            for kind in ("video", "thumbnail", "captions")
        ))
        batch = getattr(self.service.storage, "signed_urls", None)
        return batch(keys) if batch else {
            key: self.service.storage.signed_url(key) for key in keys
        }

    def _project(self, user_id, video, signed):
        return VariantCandidate.model_validate(
            {
                **video,
                "playback": {
                    "kind": "mp4",
                    "asset_id": video["asset_id"],
                    "url": signed[video["assets"]["video"]["key"]],
                    "expires_at": (datetime.now(UTC) + timedelta(seconds=600)).isoformat(),
                    "mime_type": "video/mp4",
                },
                "thumbnail_url": signed[video["assets"]["thumbnail"]["key"]],
                "captions_ref": signed[video["assets"]["captions"]["key"]],
            }
        )

    def list_variants(self, user_id, objective_ids):
        videos = self.service.repository.list_videos(user_id, objective_ids)
        signed = self._sign_owned(videos) if videos else {}
        return [self._project(user_id, video, signed) for video in videos]

    def get_variant(self, user_id, video_id):
        video = self.service.repository.video(video_id, user_id)
        return self._project(user_id, video, self._sign_owned([video])) if video else None

    def resolve_playback(self, user_id, video_id):
        try:
            return Playback.model_validate(self.service.playback(user_id, video_id))
        except LookupError:
            return None
