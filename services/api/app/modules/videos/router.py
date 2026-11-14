"""Mount with create_app(domain_routers=(create_router(video_service),))."""

from fastapi import APIRouter, HTTPException

from app.core.dependencies import CurrentUser


def create_router(service):
    router = APIRouter(prefix="/v1/learning/videos", tags=["videos"])

    @router.get("/{video_id}")
    def video(video_id: str, user: CurrentUser):
        try:
            return service.get_video(user.user_id, video_id)
        except LookupError:
            raise HTTPException(404, "Video not found") from None

    @router.get("/{video_id}/playback")
    def playback(video_id: str, user: CurrentUser):
        try:
            return service.playback(user.user_id, video_id)
        except LookupError:
            raise HTTPException(404, "Video not found") from None

    return router
