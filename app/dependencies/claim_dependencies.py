from typing import Annotated

from fastapi import Query

from app.schemas.claim_schema import ClaimSearchQueryParams
from app.schemas.common_schema import OptionalDateQuery


def get_claim_search_params(
    authNum: Annotated[str | None, Query()] = None,
    startDate: OptionalDateQuery = None,
    endDate: OptionalDateQuery = None,
    recent: Annotated[bool, Query()] = False,
    excludeTestClaims: Annotated[bool, Query()] = True,
) -> ClaimSearchQueryParams:
    return ClaimSearchQueryParams(
        authNum=authNum,
        startDate=startDate,
        endDate=endDate,
        recent=recent,
        excludeTestClaims=excludeTestClaims,
    )
