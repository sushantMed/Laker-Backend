from typing import Generic, TypeVar

from pydantic import Field
from pydantic.generics import GenericModel

from app.utils.pagination import (
    PagedResponse,
    PaginationMeta,
    PaginationRequest,
    SortRequest,
)

T = TypeVar("T")
TSearch = TypeVar("TSearch")

# class SortRequest(BaseModel):
#     sort_by: str = Field(default="id", alias="sortBy")
#     sort_dir: str = Field(default="ASC", alias="sortDir", pattern="^(ASC|DESC)$")
#     model_config = {"populate_by_name": True}


# class PaginationRequest(BaseModel):
#     page: int = Field(default=1, ge=1)
#     page_size: int = Field(default=20, ge=1, le=100, alias="pageSize")
#     model_config = {"populate_by_name": True}

#     @property
#     def offset(self) -> int:
#         return (self.page - 1) * self.page_size


# class PaginationMeta(BaseModel):
#     page: int
#     page_size: int = Field(serialization_alias="pageSize")
#     total: int
#     total_pages: int = Field(serialization_alias="totalPages")
#     has_next: bool = Field(serialization_alias="hasNext")
#     has_prev: bool = Field(serialization_alias="hasPrev")
#     model_config = {"populate_by_name": True}

#     @classmethod
#     def build(cls, *, page: int, page_size: int, total: int) -> "PaginationMeta":
#         total_pages = math.ceil(total / page_size) if page_size else 0
#         return cls(
#             page=page,
#             page_size=page_size,
#             total=total,
#             total_pages=total_pages,
#             has_next=page < total_pages,
#             has_prev=page > 1,
#         )


# class PagedResponse(BaseModel, Generic[T]):
#     data: list[T]
#     pagination: PaginationMeta

#     @classmethod
#     def of(cls, *, data: list[T], page: int, page_size: int, total: int) -> "PagedResponse[T]":
#         return cls(
#             data=data,
#             pagination=PaginationMeta.build(page=page, page_size=page_size, total=total),
#         )


class SearchRequest(GenericModel, Generic[TSearch]):
    """
    Generic search envelope used by all search endpoints.

    {
      "UserSearch":   { ... },   # or MemberSearch / ClaimSearch
      "sort":       { "sortBy": "lastName", "sortDir": "ASC" },
      "pagination": { "page": 1, "pageSize": 20 }
    }
    """

    searchRequest: TSearch

    sort: SortRequest = Field(default_factory=SortRequest)

    pagination: PaginationRequest = Field(default_factory=PaginationRequest)


class ApiResponse(GenericModel, Generic[T]):
    success: bool
    message: str
    data: T | None = None
    errors: list[str] = []

    @classmethod
    def ok(cls, data: T, message: str = "Success") -> "ApiResponse[T]":
        return cls(success=True, message=message, data=data)

    @classmethod
    def fail(cls, message: str, errors: list[str] | None = None) -> "ApiResponse[None]":
        return cls(success=False, message=message, data=None, errors=errors or [])


class PagedApiResponse(GenericModel, Generic[T]):
    success: bool
    message: str
    data: list[T]  # flat list, no nesting
    pagination: PaginationMeta  # top level
    errors: list[str] = []

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
            errors=[],
        )

    @classmethod
    def fail(
        cls,
        message: str,
        errors: list[str] | None = None,
    ) -> "PagedApiResponse[None]":
        return cls(
            success=False,
            message=message,
            data=[],
            pagination=PaginationMeta(
                page=1,
                pageSize=20,
                total=0,
                totalPages=0,
                hasNext=False,
                hasPrev=False,
            ),
            errors=errors or [],
        )
