from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import Settings
from app.core.database import Database
from app.core.errors import install_error_handlers
from app.core.identity import FixtureIdentity, IdentityVerifier, UnconfiguredIdentity
from app.core.middleware import RequestBoundary
from app.core.time import utc_now
from app.modules.quizzes.adapters import EmptyQuizzes, QuizReader
from app.modules.quizzes.router import progress_router
from app.modules.quizzes.router import router as quiz_router
from app.modules.quizzes.service import QuizService
from app.modules.recommendations.adapters import (
    AcademicReader,
    EmptyAcademics,
    EmptyEntertainment,
    EmptyVideos,
    EntertainmentReader,
    VideoReader,
)
from app.modules.recommendations.events import PlaybackEvents
from app.modules.recommendations.router import router as feed_router
from app.modules.recommendations.service import FeedService


def create_app(
    *,
    settings: Settings | None = None,
    database: Database | None = None,
    identity: IdentityVerifier | None = None,
    academics: AcademicReader | None = None,
    entertainment: EntertainmentReader | None = None,
    videos: VideoReader | None = None,
    quiz_reader: QuizReader | None = None,
    domain_routers: tuple[APIRouter, ...] = (),
    close_database: bool = False,
    require_identity_catalog: bool = False,
    clock=utc_now,
) -> FastAPI:
    settings = settings or Settings()
    owns_database = database is None or close_database
    database = database or Database(settings)
    if settings.environment == "fixture":
        from app.core.fixtures import FixtureCatalog

        catalog = FixtureCatalog()
        identity = identity or FixtureIdentity(settings)
        academics = academics or catalog
        entertainment = entertainment or catalog
        videos = videos or catalog
        quiz_reader = quiz_reader or catalog
    if settings.environment == "production" and isinstance(
        identity, (FixtureIdentity, UnconfiguredIdentity)
    ):
        raise ValueError("Production requires a real identity adapter")
    if settings.environment == "production" and identity is None:
        raise ValueError("Production requires an explicitly configured identity adapter")

    @asynccontextmanager
    async def lifespan(app):
        try:
            if settings.environment in {"test", "fixture"}:
                database.initialize_local()
            database.verify_ready()
            if require_identity_catalog:
                from app.modules.auth.atlas_preflight import owned_schema_checks

                checks = owned_schema_checks(database.mongo)
                if not all(all(result.values()) for result in checks.values()):
                    raise RuntimeError(
                        "Apply identity/catalog migrations before starting this service"
                    )
            yield
        finally:
            if owns_database:
                database.close()

    app = FastAPI(
        title="Learning Feed API",
        version="0.1.0",
        lifespan=lifespan,
        docs_url=None if settings.environment == "production" else "/docs",
        redoc_url=None,
    )
    app.state.database = database
    app.state.clock = clock
    app.state.identity = identity or UnconfiguredIdentity()
    academics = academics or EmptyAcademics()
    videos = videos or EmptyVideos()
    app.state.feed = FeedService(
        database,
        academics,
        entertainment or EmptyEntertainment(),
        videos,
        quiz_reader or EmptyQuizzes(),
        clock=clock,
    )
    app.state.playback_events = PlaybackEvents(database, clock)
    app.state.quizzes = QuizService(database, academics, videos, clock)
    app.add_middleware(
        RequestBoundary,
        max_body_bytes=settings.max_body_bytes,
        production=settings.environment == "production",
    )
    if settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_methods=["GET", "POST", "PATCH", "DELETE"],
            allow_headers=["Authorization", "Content-Type", "Idempotency-Key"],
            expose_headers=["X-Request-ID", "Retry-After"],
        )
    install_error_handlers(app)

    @app.get("/health", tags=["operations"])
    def health():
        return {"status": "ok", "schema_version": "1", "mode": settings.environment}

    app.include_router(feed_router)
    app.include_router(quiz_router)
    app.include_router(progress_router)
    # The owning teams supply their routers. Do not import/modify guessed internals.
    for router in domain_routers:
        app.include_router(router)
    return app
