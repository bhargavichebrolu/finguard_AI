"""The FastAPI application.

Start-up loads and verifies the frozen model. It never trains, and it never changes the schema:
migrations run separately. If any check fails, the application does not start.
"""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from app.api.router import api_router
from app.core.config import APP_VERSION, get_settings
from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging
from app.core.middleware import RequestContextMiddleware
from app.database.session import session_scope
from app.services.batch_service import BatchWorker, remove_stale_uploads
from app.services.model_service import load_verified_model, register_active_model

logger = logging.getLogger("finguard.startup")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Prepare everything a request needs, before the first request is accepted."""
    settings = get_settings()
    model = load_verified_model(settings)
    with session_scope() as session:
        register_active_model(session, model)
    # Phase 5 M4: start-up no longer fails unfinished jobs. Another process may be working on
    # them; any job whose lease expires is resumed by whichever worker claims it next.
    removed = remove_stale_uploads(settings.upload_tmp_dir)
    if removed:
        logger.warning("Removed %d temporary upload files left by interrupted requests", removed)
    app.state.model = model
    app.state.batch_worker = None
    if settings.batch_worker_enabled:
        app.state.batch_worker = BatchWorker(model, settings)
        app.state.batch_worker.start()
        logger.info("Batch worker %s started", app.state.batch_worker.worker_id)
    logger.info("Model %s verified and loaded", model.version)
    yield
    if app.state.batch_worker is not None:
        # Finish the current chunk and give the job back, so another process resumes it at once.
        app.state.batch_worker.stop()


def create_app() -> FastAPI:
    """Build the application."""
    configure_logging()
    settings = get_settings()
    # Off in production (security finding S13): no interactive pages and no schema endpoint.
    docs = settings.docs_enabled
    app = FastAPI(
        title="FinGuard AI API",
        version=APP_VERSION,
        lifespan=lifespan,
        docs_url="/docs" if docs else None,
        redoc_url="/redoc" if docs else None,
        openapi_url="/openapi.json" if docs else None,
        description=(
            "Scores simulated transactions for human review. `model_score` is uncalibrated and is "
            "not a probability of fraud. `FLAG_FOR_REVIEW` is a request for review, not a finding. "
            "Trained and evaluated on the synthetic PaySim dataset."
        ),
    )
    register_exception_handlers(app)
    app.include_router(api_router)
    app.add_middleware(RequestContextMiddleware)
    # Added last so it wraps everything, which keeps CORS headers on early refusals too.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-CSRF-Token"],
    )
    if settings.trusted_proxies:
        # Outermost, so every later step sees the client address the trusted proxy reported.
        app.add_middleware(ProxyHeadersMiddleware, trusted_hosts=settings.trusted_proxies)
    return app


app = create_app()
