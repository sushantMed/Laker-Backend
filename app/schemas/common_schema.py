from datetime import date, datetime
from typing import Annotated, Generic, TypeVar

from fastapi import Query
from pydantic import BeforeValidator, Field
from pydantic.generics import GenericModel

from app.core.base_model import AppBaseModel as BaseModel
from app.utils.pagination import (
    PagedResponse,
    PaginationMeta,
    PaginationRequest,
    SortRequest,
)

T = TypeVar("T")
TSearch = TypeVar("TSearch")


_PLACEHOLDER_VALUES = {
    "mm/dd/yyyy",
    "dd/mm/yyyy",
    "yyyy-mm-dd",
    "select date",
    "dd-mm-yyyy",
    "mm-dd-yyyy",
}

# Formats to try, in order. Add more here if you spot other patterns
# coming from the frontend (check network tab / logs).
_KNOWN_FORMATS = (
    "%m/%d/%Y",  # 05/18/2026  (what the frontend actually sends)
    "%Y-%m-%d",  # 2026-05-18  (ISO, in case some callers send this)
    "%d/%m/%Y",  # 18/05/2026  (just in case, low priority)
)


def _parse_flexible_date(v: str | date | None) -> date | None:
    """
    Accepts a date query param in whatever format the frontend happens
    to send, since we can't fix the frontend to send ISO dates.

    - Blank strings and known placeholder text (e.g. 'mm/dd/yyyy') -> None
    - Recognized formats (currently MM/DD/YYYY) -> parsed date
    - Already a date object -> passed through
    - Anything else unparseable -> None (fail open rather than 422,
      since we can't guarantee what junk the frontend might send)
    """
    if v is None or isinstance(v, date):
        return v

    if not isinstance(v, str):
        return v

    raw = v.strip()
    if raw == "" or raw.lower() in _PLACEHOLDER_VALUES:
        return None

    for fmt in _KNOWN_FORMATS:
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue

    # Nothing matched - treat as not provided rather than 500/422ing
    # on a value we don't control the format of.
    return None


OptionalDateQuery = Annotated[
    date | None,
    BeforeValidator(_parse_flexible_date),
    Query(),
]


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
    otpVerificationAttemptsRemaining: int | None = None
    otpResendAttemptsRemaining: int | None = None


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
        otp_verification_attempts_remaining: int | None = None,
        otp_resend_attempts_remaining: int | None = None,
    ) -> "ApiResponse[None]":
        return cls(
            success=False,
            message=message,
            data=None,
            error=ErrorDetail(
                statusCode=status_code,
                message=exception_message or message,
                otpVerificationAttemptsRemaining=otp_verification_attempts_remaining,
                otpResendAttemptsRemaining=otp_resend_attempts_remaining,
            ),
        )


class PagedApiResponse(GenericModel, Generic[T]):
    model_config = {"populate_by_name": True}

    success: bool
    message: str
    data: list[T]  # flat list, no nesting
    pagination: PaginationMeta | None = None
    recent_claim_count: int | None = Field(None, alias="recentClaimCount")
    error: ErrorDetail | None = None

    @classmethod
    def ok(
        cls,
        data: PagedResponse[T],
        message: str = "Success",
        recent_claim_count: int | None = None,
    ) -> "PagedApiResponse[T]":
        return cls(
            success=True,
            message=message,
            data=data.data,
            pagination=data.pagination,
            recent_claim_count=recent_claim_count,
            error=None,
        )

    @classmethod
    def fail(
        cls,
        message: str,
        status_code: int = 200,
        errors: list[str] | None = None,
    ) -> "PagedApiResponse[None]":
        return cls(
            success=False,
            message=message,
            data=None,
            pagination=None,
            error=ErrorDetail(
                statusCode=status_code,
                message="; ".join(errors) if errors else message,
            ),
        )
