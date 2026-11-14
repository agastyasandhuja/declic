from fastapi import APIRouter, Depends, Query


def create_entertainment_router(current_user, catalog):
    router = APIRouter(prefix='/v1/entertainment')
    @router.get('/feed')
    def feed(cursor: str | None = Query(None, max_length=2048), limit: int = Query(5, ge=1, le=20), user=Depends(current_user)):
        return catalog.list_candidates(user, cursor, limit)
    @router.get('/videos/{video_id}/playback')
    def playback(video_id: str, user=Depends(current_user)):
        return catalog.resolve_playback(video_id, user)
    @router.get('/videos/{video_id}/comments')
    def comments(video_id: str, cursor: str | None = Query(None, max_length=256), limit: int = Query(20, ge=1, le=20), user=Depends(current_user)):
        reader = getattr(catalog, 'comments', None)
        if reader is None:
            return {'schema_version': '1', 'items': [], 'next_cursor': None,
                    'availability': 'unavailable', 'reason': 'comments_not_supported'}
        return reader.read(user['user_id'], video_id, cursor, limit)
    return router
