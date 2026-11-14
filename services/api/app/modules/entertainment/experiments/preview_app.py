"""Temporary local assembly; Agastya retains ownership of shared API core/main."""
from pathlib import Path
from contextlib import asynccontextmanager
import os
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException

from app.modules.auth.router import create_identity_router, make_current_user
from app.modules.auth.service import AuthFailure, SupabaseVerifier
from app.modules.entertainment.router import create_entertainment_router
from app.modules.entertainment.service import CatalogFailure, SavedCatalog

ROOT = Path(__file__).resolve().parents[6]


def mobile_configuration():
    values = {}
    for line in (ROOT / 'apps/mobile/.env').read_text().splitlines():
        key, separator, value = line.partition('=')
        if separator and key.strip().startswith('EXPO_PUBLIC_SUPABASE_'):
            values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def supabase_configuration():
    # Resolve each public setting independently so a URL-only server override
    # doesn't discard the mobile publishable key before setup can explain it.
    values = mobile_configuration() if not os.environ.get('SUPABASE_URL') or not os.environ.get('SUPABASE_PUBLISHABLE_KEY') else {}
    return (os.environ.get('SUPABASE_URL') or values.get('EXPO_PUBLIC_SUPABASE_URL', ''),
            os.environ.get('SUPABASE_PUBLISHABLE_KEY') or values.get('EXPO_PUBLIC_SUPABASE_PUBLISHABLE_KEY', ''))


def create_preview_app(verifier=None, catalog=None, profiles=None):
    @asynccontextmanager
    async def lifespan(_app):
        try:
            yield
        finally:
            if hasattr(catalog, 'close'):
                catalog.close()
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None, redirect_slashes=False, lifespan=lifespan)
    if verifier is None:
        verifier = SupabaseVerifier(*supabase_configuration())
    if catalog is None:
        directory = ROOT / '.local/instagram-probe'
        catalog = SavedCatalog(directory / 'feed.v1.json', directory / 'owner.json')
    current_user = make_current_user(verifier)
    async def domain_error(_request: Request, error):
        headers = {'Cache-Control': 'no-store'}
        if getattr(error, 'retry_after', None):
            headers['Retry-After'] = str(error.retry_after)
        return JSONResponse(status_code=error.status, content={'error': {'code': error.code, 'message': error.message, 'retryable': error.status >= 500, 'request_id': str(uuid4())}}, headers=headers)
    app.add_exception_handler(AuthFailure, domain_error)
    app.add_exception_handler(CatalogFailure, domain_error)
    @app.exception_handler(RequestValidationError)
    async def validation_error(request, error):
        return await domain_error(request, CatalogFailure(422, 'INVALID_REQUEST', 'Check the request parameters and retry.'))
    @app.exception_handler(HTTPException)
    async def http_error(request, error):
        return await domain_error(request, CatalogFailure(error.status_code, 'REQUEST_FAILED', 'This request is unavailable.'))
    @app.middleware('http')
    async def no_cache(request, call_next):
        response = await call_next(request)
        response.headers['Cache-Control'] = 'no-store'
        return response
    app.include_router(create_identity_router(current_user, profiles))
    app.include_router(create_entertainment_router(current_user, catalog))
    return app



def create_fixture_app():
    """Local fixture assembly: real Supabase verification, synthetic catalog only."""
    from app.modules.entertainment.fixtures import FixtureCatalog
    from app.modules.entertainment.service import CatalogService
    return create_preview_app(catalog=CatalogService(FixtureCatalog()))


def create_live_app():
    """Local owner-bound live assembly; shared main.py still belongs to Agastya."""
    from app.modules.entertainment.instagram_connection import DEFAULT_CONNECTION, open_live_catalog, write_private
    report_path = ROOT / '.local/instagram-live/runtime-report.json'
    catalog = open_live_catalog(os.environ.get('INSTAGRAM_CONNECTION_FILE', DEFAULT_CONNECTION),
        diagnostics=lambda value: write_private(report_path, value))
    try:
        catalog._diagnose()
        return create_preview_app(catalog=catalog)
    except Exception:
        catalog.close()
        raise
