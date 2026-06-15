import math
from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class SortRequest(BaseModel):
    sort_by: str = Field(default="id", alias="sortBy")
    sort_dir: str = Field(default="ASC", alias="sortDir", pattern="^(ASC|DESC)$")

    model_config = {"populate_by_name": True}


class PaginationRequest(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100, alias="pageSize")

    model_config = {"populate_by_name": True}

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


class PaginationMeta(BaseModel):
    page: int
    page_size: int = Field(serialization_alias="pageSize")
    total: int
    total_pages: int = Field(serialization_alias="totalPages")
    has_next: bool = Field(serialization_alias="hasNext")
    has_prev: bool = Field(serialization_alias="hasPrev")

    model_config = {"populate_by_name": True}

    @classmethod
    def build(cls, *, page: int, page_size: int, total: int) -> "PaginationMeta":
        total_pages = math.ceil(total / page_size) if page_size else 0
        return cls(
            page=page,
            page_size=page_size,
            total=total,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1,
        )


class PagedResponse(BaseModel, Generic[T]):
    data: list[T]
    pagination: PaginationMeta

    @classmethod
    def of(
        cls, *, data: list[T], page: int, page_size: int, total: int
    ) -> "PagedResponse[T]":
        return cls(
            data=data,
            pagination=PaginationMeta.build(
                page=page, page_size=page_size, total=total
            ),
        )


class FamilyMembersRequest(PaginationRequest):
    pass
