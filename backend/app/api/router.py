"""Collect every route module into one router."""

from fastapi import APIRouter

from app.api.routes import audit, auth, health, users

api_router = APIRouter()
for module in (health, auth, users, audit):
    api_router.include_router(module.router)
