from fastapi import APIRouter, Depends, Query


def create_entertainment_router(current_user, catalog):
    router = APIRouter(prefix='/v1/entertainment')
    @router.get('/feed')
    def feed(cursor: str | None = Query(None, max_length=2048), limit: int = Query(5, ge=1, le=20), user=Depends(current_user)):
        return catalog.list_candidates(user, cursor, limit)
    @router.get('/videos/{video_id}/playback')
    def playback(video_id: str, user=Depends(current_user)):
        return catalog.resolve_playback(video_id, user)
    return router
