"""Composition adapters for owner-provided identity and entertainment services."""

from app.core.errors import APIError
from app.core.identity import Principal
from app.modules.auth.service import AuthFailure
from app.modules.entertainment.service import CatalogFailure
from app.modules.recommendations.models import EntertainmentCandidate


class SupabaseIdentity:
    def __init__(self, verifier):
        self.verifier = verifier

    async def verify_access_token(self, token):
        try:
            user = await self.verifier.verify_access_token(token)
        except AuthFailure as error:
            raise APIError(
                error.status, error.code, error.message, retryable=error.status >= 500
            ) from None
        return Principal(user["user_id"], user["timezone"], identity_data=user)


class FeedEntertainmentReader:
    def __init__(self, catalog):
        self.catalog = catalog

    def list_candidates(self, user_id, limit):
        candidates, cursor = [], None
        # Adi's snapshots contain at most 100 records. Expired windows may be empty
        # while later windows still contain usable clips.
        for _ in range(5):
            try:
                page = self.catalog.list_candidates({"user_id": user_id}, cursor, 20)
            except CatalogFailure as error:
                if error.code == "CATALOG_NOT_FOUND":
                    return []
                raise APIError(
                    error.status, error.code, error.message, retryable=error.status >= 500
                ) from None
            candidates.extend(EntertainmentCandidate.model_validate(item) for item in page["items"])
            cursor = page["next_cursor"]
            if len(candidates) >= limit or cursor is None:
                break
        return candidates[:limit]
