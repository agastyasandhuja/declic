"""Configured Atlas API: uvicorn app.runtime:create_app --factory."""

from app.core.config import Settings
from app.core.database import Database
from app.core.dependencies import CurrentUser
from app.core.errors import APIError, error_response
from app.core.integration import FeedEntertainmentReader, SupabaseIdentity
from app.main import create_app as create_core_app
from app.modules.auth.repository import ProfileRepository
from app.modules.auth.router import create_identity_router
from app.modules.auth.service import AuthFailure, SupabaseVerifier
from app.modules.entertainment.repository import CatalogRepository
from app.modules.entertainment.router import create_entertainment_router
from app.modules.entertainment.service import CatalogFailure, CatalogService


def verified_record(user: CurrentUser):
    # This dependency shares core verification/rate limiting with feed and quizzes.
    return {**(user.identity_data or {}), "user_id": user.user_id, "timezone": user.timezone}


def create_app(*, settings=None, database=None, verifier=None):
    settings = settings or Settings()
    if settings.persistence != "mongodb" or settings.environment in {"fixture", "test"}:
        raise ValueError("Integrated runtime requires MongoDB in development or production")
    if settings.environment == "production" and settings.catalog_cursor_secret is None:
        raise ValueError("Configure API_CATALOG_CURSOR_SECRET for stable production cursors")
    if verifier is None:
        if not settings.supabase_url or settings.supabase_publishable_key is None:
            raise ValueError("Configure SUPABASE_URL and SUPABASE_PUBLISHABLE_KEY")
        verifier = SupabaseVerifier(
            settings.supabase_url, settings.supabase_publishable_key.get_secret_value()
        )
    owns_database = database is None
    database = database or Database(settings)
    try:
        profiles = ProfileRepository(database.mongo)
        catalog = CatalogService(
            CatalogRepository(database.mongo),
            cursor_secret=settings.catalog_cursor_secret.get_secret_value().encode()
            if settings.catalog_cursor_secret else None,
        )
        app = create_core_app(
            settings=settings,
            database=database,
            identity=SupabaseIdentity(verifier),
            entertainment=FeedEntertainmentReader(catalog),
            domain_routers=(
                create_identity_router(verified_record, profiles),
                create_entertainment_router(verified_record, catalog),
            ),
            close_database=owns_database,
            require_identity_catalog=True,
        )
    except BaseException:
        if owns_database:
            database.close()
        raise

    async def owner_error(request, error):
        return error_response(
            request,
            APIError(error.status, error.code, error.message, retryable=error.status >= 500),
        )

    app.add_exception_handler(AuthFailure, owner_error)
    app.add_exception_handler(CatalogFailure, owner_error)
    return app
