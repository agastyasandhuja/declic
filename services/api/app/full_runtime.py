"""Complete cloud-backed API assembly for the local Mac demo."""

import os
from pathlib import Path

from app.core.academic_jobs import AcademicJobs
from app.core.config import Settings
from app.core.connections import Connections
from app.core.connections import create_router as canvas_router
from app.core.credential_vault import CredentialVault
from app.core.database import Database
from app.core.environment import ROOT, load_environment
from app.core.errors import APIError, error_response
from app.core.integration import FeedEntertainmentReader, SupabaseIdentity
from app.core.learning_pipeline import LearningPipeline, StoredQuizzes
from app.core.learning_readers import BoundVideoReader
from app.core.preparation import create_router as preparation_router
from app.core.semantic_topics import GeminiEmbeddings, SemanticTopics
from app.core.social_connections import SocialConnections
from app.core.social_connections import create_router as social_router
from app.main import create_app as core_app
from app.modules.auth.repository import ProfileRepository
from app.modules.auth.router import create_identity_router
from app.modules.auth.service import AuthFailure, SupabaseVerifier
from app.modules.canvas.config import normalize_origin
from app.modules.curriculum.adapters import FeedAcademicReader
from app.modules.curriculum.client.gemini import GeminiClient
from app.modules.curriculum.config import load_settings
from app.modules.curriculum.router import create_router as academic_router
from app.modules.curriculum.service import AcademicService
from app.modules.curriculum.store import use_atlas
from app.modules.entertainment.repository import CatalogRepository
from app.modules.entertainment.router import create_entertainment_router
from app.modules.entertainment.service import CatalogFailure, CatalogService
from app.modules.videos.publication import SupabaseVideoStorage
from app.modules.videos.repository import AtlasVideoRepository
from app.modules.videos.router import create_router as video_router
from app.modules.videos.service import VideoService
from app.runtime import verified_record


class UnconfiguredGemini:
    def generate_json(self, **kwargs):
        raise RuntimeError(
            "Configure services/api/.env.gemini.local before starting academic workers"
        )


def components(settings=None):
    load_environment()
    settings = settings or Settings()
    database = Database(settings)
    use_atlas(database.mongo)
    vault = CredentialVault(os.environ["CONNECTION_ENCRYPTION_KEY"])
    origin = normalize_origin(os.getenv("CANVAS_BASE_URL", "https://umamherst.instructure.com"))
    connections = Connections(database, vault, origin)
    client = GeminiClient(load_settings()) if os.getenv("GEMINI_API_KEY") else UnconfiguredGemini()
    academics = AcademicService(
        Path(os.getenv("APP_PRIVATE_DATA_DIR", ROOT / ".local/academics")), client
    )
    repository = AtlasVideoRepository(database.mongo)
    storage = SupabaseVideoStorage()
    video_service = VideoService(repository, academics, storage)
    topics = SemanticTopics(database, GeminiEmbeddings(os.getenv("GEMINI_API_KEY", "")))
    pipeline = LearningPipeline(database, connections, academics, client, topics, repository)
    pipeline.social = SocialConnections(database, vault)
    return database, connections, academics, video_service, pipeline


def create_app():
    database, connections, academics, videos, pipeline = components()
    settings = database.settings
    profiles = ProfileRepository(database.mongo)
    catalog = CatalogService(
        CatalogRepository(database.mongo),
        cursor_secret=settings.catalog_cursor_secret.get_secret_value().encode()
        if settings.catalog_cursor_secret
        else None,
    )
    app = core_app(
        settings=settings,
        database=database,
        close_database=True,
        identity=SupabaseIdentity(
            SupabaseVerifier(
                settings.supabase_url, settings.supabase_publishable_key.get_secret_value()
            )
        ),
        academics=FeedAcademicReader(academics),
        entertainment=FeedEntertainmentReader(catalog),
        videos=BoundVideoReader(videos, database),
        quiz_reader=StoredQuizzes(database),
        domain_routers=(
            create_identity_router(verified_record, profiles),
            create_entertainment_router(verified_record, catalog),
            canvas_router(connections),
            academic_router(academics, AcademicJobs(database)),
            video_router(videos),
            social_router(pipeline.social),
            preparation_router(database),
        ),
        require_identity_catalog=True,
    )
    app.state.learning_pipeline = pipeline

    async def owner_error(request, error):
        return error_response(
            request,
            APIError(error.status, error.code, error.message, retryable=error.status >= 500),
        )

    app.add_exception_handler(AuthFailure, owner_error)
    app.add_exception_handler(CatalogFailure, owner_error)
    return app
