from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, ConfigDict, Field, StrictInt, StrictStr

from .service import AuthFailure


def make_current_user(verifier):
    async def current_user(request: Request):
        parts = request.headers.get('Authorization', '').split()
        if len(parts) != 2 or parts[0].lower() != 'bearer':
            raise AuthFailure(401, 'AUTH_REQUIRED', 'Sign in to access your private feed.')
        return await verifier.verify_access_token(parts[1])
    return current_user


class ProfilePatch(BaseModel):
    model_config = ConfigDict(extra='forbid')
    expected_revision: StrictInt = Field(ge=0)
    display_name: StrictStr | None = Field(default=None, max_length=80)
    timezone: StrictStr | None = None


def create_identity_router(current_user, profiles=None):
    router = APIRouter()
    @router.get('/v1/me')
    def me(user=Depends(current_user)):
        return {'schema_version': '1', **(profiles.get_profile(user) if profiles else user)}
    @router.patch('/v1/me')
    def update_me(patch: ProfilePatch, user=Depends(current_user)):
        if profiles is None:
            raise AuthFailure(503, 'PROFILE_UNAVAILABLE', 'Profile storage is not configured yet.')
        changes = patch.model_dump(exclude_unset=True, exclude={'expected_revision'})
        return {'schema_version': '1', **profiles.update_profile(user, patch.expected_revision, changes)}
    return router
