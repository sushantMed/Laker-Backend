from typing import Generic, TypeVar

from pydantic import BaseModel, Field
from pydantic.generics import GenericModel

from app.utils.pagination import (
    PagedResponse,
    PaginationMeta,
    PaginationRequest,
    SortRequest,
)

T = TypeVar("T")
TSearch = TypeVar("TSearch")


class SearchRequest(GenericModel, Generic[TSearch]):
    """
    Generic search envelope used by all search endpoints.

    {
      "searchRequest": { ... },   # e.g. MemberSearch / ClaimSearch
      "sort":       { "sortBy": "lastName", "sortDir": "ASC" },
      "pagination": { "page": 1, "pageSize": 20 }
    }
    """

    searchRequest: TSearch
    sort: SortRequest = Field(default_factory=SortRequest)
    pagination: PaginationRequest = Field(default_factory=PaginationRequest)


class ErrorDetail(BaseModel):
    statusCode: int
    message: str


class ApiResponse(GenericModel, Generic[T]):
    success: bool
    message: str
    data: T | None = None
    error: ErrorDetail | None = None

    @classmethod
    def ok(
        cls,
        data: T | None = None,
        message: str = "Success",
    ) -> "ApiResponse[T]":
        return cls(
            success=True,
            message=message,
            data=data,
            error=None,
        )

    @classmethod
    def fail(
        cls,
        message: str,
        status_code: int = 400,
        exception_message: str | None = None,
    ) -> "ApiResponse[None]":
        return cls(
            success=False,
            message=message,
            data=None,
            error=ErrorDetail(
                statusCode=status_code,
                message=exception_message or message,
            ),
        )


class PagedApiResponse(GenericModel, Generic[T]):
    success: bool
    message: str
    data: list[T]  # flat list, no nesting
    pagination: PaginationMeta | None = None
    error: ErrorDetail | None = None

    @classmethod
    def ok(
        cls,
        data: PagedResponse[T],
        message: str = "Success",
    ) -> "PagedApiResponse[T]":
        return cls(
            success=True,
            message=message,
            data=data.data,
            pagination=data.pagination,
            error=None,
        )

    @classmethod
    def fail(
        cls,
        message: str,
        status_code: int = 400,
        errors: list[str] | None = None,
    ) -> "PagedApiResponse[None]":
        return cls(
            success=False,
            message=message,
            data=[],
            pagination=None,
            error=ErrorDetail(
                statusCode=status_code,
                message="; ".join(errors) if errors else message,
            ),
        )
