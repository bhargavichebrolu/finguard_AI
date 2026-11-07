"""The FastAPI application.

Start-up loads and verifies the frozen model. It never trains, and it never changes the schema:
migrations run separately. If any check fails, the application does not start.
"""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import APP_VERSION, get_settings
from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging
from app.core.middleware import RequestContextMiddleware
from app.database.session import session_scope
from app.services.model_service import load_verified_model, register_active_model

logger = logging.getLogger("finguard.startup")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Prepare everything a request needs, before the first request is accepted."""
    settings = get_settings()
    model = load_verified_model(settings)
    with session_scope() as session:
        register_active_model(session, model)
    app.state.model = model
    logger.info("Model %s verified and loaded", model.version)
    yield


def create_app() -> FastAPI:
    """Build the application."""
    configure_logging()
    settings = get_settings()
    app = FastAPI(
        title="FinGuard AI API",
        version=APP_VERSION,
        lifespan=lifespan,
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
        allow_credentials=False,
        allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )
    return app


app = create_app()
