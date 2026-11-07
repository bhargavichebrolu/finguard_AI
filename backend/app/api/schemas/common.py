"""Schemas and query parameters shared by several routes."""

from typing import Annotated, Generic, TypeVar

from fastapi import Query
from pydantic import BaseModel, ConfigDict

ItemT = TypeVar("ItemT")

MAX_PAGE_SIZE = 200
Limit = Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE, description="Rows per page")]
Offset = Annotated[int, Query(ge=0, description="Rows to skip")]


class ApiModel(BaseModel):
    """Base for response schemas, which can be built directly from database rows."""

    model_config = ConfigDict(from_attributes=True, protected_namespaces=())


class Page(ApiModel, Generic[ItemT]):
    """One page of results."""

    items: list[ItemT]
    total: int
    limit: int
    offset: int


class ErrorResponse(BaseModel):
    """The shape of every error response."""

    detail: str
    request_id: str | None = None
