from __future__ import annotations

from datetime import date, datetime

from pydantic import ConfigDict, Field, field_validator, model_validator  # type: ignore
from pydantic.alias_generators import to_camel  # type: ignore

from app.core.base_model import AppBaseModel as BaseModel
from app.schemas.common_schema import SearchRequest
from app.utils.pagination import PaginationRequest, SortRequest

_CAMEL = {"populate_by_name": True}


class CardPrintHistoryRow(BaseModel):
    """One row of the Card Print History grid.

    changeDate / printDate / batchNum / cardCancelled are the four columns the
    legacy screen renders; cardQueueKey identifies the row for the cancel
    endpoint and reportStatus carries the raw CARDQ status behind
    cardCancelled.
    """

    model_config = _CAMEL

    card_queue_key: str = Field(alias="cardQueueKey")
    change_date: datetime | None = Field(None, alias="changeDate")
    print_date: date | None = Field(None, alias="printDate")
    batch_num: int | None = Field(None, alias="batchNum")
    card_cancelled: bool = Field(alias="cardCancelled")
    report_status: str | None = Field(None, alias="reportStatus")


class CardPrintHistorySearch(BaseModel):
    """Optional filters for the Card Print History search.

    Every field is optional -- an empty body returns the member's full history,
    which is what the legacy screen does.
    """

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "changeDateFrom": None,
                "changeDateTo": None,
                "batchNum": None,
                "cardCancelled": None,
            }
        },
    )

    change_date_from: date | None = None
    change_date_to: date | None = None
    batch_num: int | None = None
    card_cancelled: bool | None = None

    @field_validator("change_date_from", "change_date_to", mode="before")
    @classmethod
    def blank_date_to_none(cls, v):
        """An untouched date box posts "" -- treat it as no filter, not a 422."""
        if isinstance(v, str) and not v.strip():
            return None
        return v

    @field_validator("batch_num", mode="before")
    @classmethod
    def blank_batch_num_to_none(cls, v):
        if isinstance(v, str) and not v.strip():
            return None
        return v

    @model_validator(mode="after")
    def validate_change_date_range(self) -> CardPrintHistorySearch:
        if (
            self.change_date_from
            and self.change_date_to
            and self.change_date_to < self.change_date_from
        ):
            from app.core.exceptions import InvalidDateRangeException

            raise InvalidDateRangeException(
                f"changeDateTo ({self.change_date_to}) must be >= "
                f"changeDateFrom ({self.change_date_from})."
            )
        return self


class CardPrintHistorySearchRequest(BaseModel, SearchRequest[CardPrintHistorySearch]):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "searchRequest": {
                    "changeDateFrom": None,
                    "changeDateTo": None,
                    "batchNum": None,
                    "cardCancelled": None,
                },
                "sort": {"sortBy": "changeDate", "sortDir": "DESC"},
                "pagination": {"page": 1, "pageSize": 20},
            }
        },
    )

    searchRequest: CardPrintHistorySearch = Field(
        default_factory=CardPrintHistorySearch
    )
    # The grid reads newest-first, so an omitted sort means changeDate DESC
    # rather than the shared "id ASC" default.
    sort: SortRequest = Field(
        default_factory=lambda: SortRequest(sortBy="changeDate", sortDir="DESC")
    )


class CardPrintHistoryQuery(BaseModel, PaginationRequest):
    """Query params for the plain GET listing."""

    model_config = _CAMEL
