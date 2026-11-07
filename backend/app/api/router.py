"""Collect every route module into one router."""

from fastapi import APIRouter

from app.api.routes import (
    audit,
    auth,
    batches,
    health,
    investigations,
    models,
    reports,
    settings,
    transactions,
    users,
)

api_router = APIRouter()
for module in (
    health,
    auth,
    users,
    transactions,
    batches,
    investigations,
    models,
    reports,
    settings,
    audit,
):
    api_router.include_router(module.router)
