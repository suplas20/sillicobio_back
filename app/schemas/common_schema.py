from typing import Generic, TypeVar

from pydantic import BaseModel


T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    total: int
    page: int
    size: int
    items: list[T]


class ErrorDetail(BaseModel):
    field: str | None = None
    reason: str


class ErrorResponse(BaseModel):
    code: str
    message: str
    details: list[ErrorDetail] | None = None
