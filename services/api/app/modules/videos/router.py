"""Mount with create_app(domain_routers=(create_router(video_service),))."""

from fastapi import APIRouter, HTTPException, Request

from app.core.dependencies import CurrentUser
from app.core.errors import APIError, error_response


def create_router(service, *, demo=None, learning_settings=None):
    router = APIRouter(prefix="/v1/learning/videos", tags=["videos"])

    @router.get("/{video_id}")
    def video(video_id: str, user: CurrentUser):
        try:
            return service.get_video(user.user_id, video_id)
        except LookupError:
            raise HTTPException(404, "Video not found") from None

    @router.get("/{video_id}/playback")
    def playback(video_id: str, user: CurrentUser, request: Request):
        if demo is not None and learning_settings.enabled(user.user_id):
            try:
                playback = demo.resolve_playback(user.user_id, video_id)
            except APIError as error:
                return error_response(request, error)
            if playback is None:
                return error_response(
                    request, APIError(404, "VIDEO_NOT_FOUND", "Video not found in the demo")
                )
            return playback.model_dump(mode="json")
        try:
            return service.playback(user.user_id, video_id)
        except LookupError:
            return error_response(request, APIError(404, "VIDEO_NOT_FOUND", "Video not found"))

    return router
