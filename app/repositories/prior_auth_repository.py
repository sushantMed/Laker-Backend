from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from decimal import Decimal

from sqlalchemy import String, and_, asc, cast, desc, func, literal, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.drug_model import DrugModel
from app.models.prior_auth_model import PriorAuthModel
from app.utils.enums import PA_ACTION_AUTHORIZED, PA_ACTION_DECLINED, PAStatus

_SORTABLE_COLUMNS = {
    "paId": PriorAuthModel.authnum,
    "memberId": PriorAuthModel.subscribernum,
    "drugName": PriorAuthModel.genname,
    "ndc": PriorAuthModel.ndc,
    "effDate": PriorAuthModel.effdate,
    "termDate": PriorAuthModel.termdate,
}
_DEFAULT_SORT_COLUMN = PriorAuthModel.effdate

_ACTION = func.coalesce(PriorAuthModel.action, "")
_DENIAL = func.coalesce(PriorAuthModel.denial, "")


def _status_clause(status: PAStatus, today: date):
    declined = or_(_ACTION == PA_ACTION_DECLINED, _DENIAL != "")
    authorized = and_(_ACTION == PA_ACTION_AUTHORIZED, _DENIAL == "")

    if status is PAStatus.DECLINED:
        return declined
    if status is PAStatus.PENDING:
        return and_(
            _ACTION != PA_ACTION_AUTHORIZED,
            _ACTION != PA_ACTION_DECLINED,
            _DENIAL == "",
        )
    if status is PAStatus.EXPIRED:
        return and_(
            authorized,
            PriorAuthModel.termdate.isnot(None),
            PriorAuthModel.termdate < today,
        )
    return and_(
        authorized,
        or_(PriorAuthModel.termdate.is_(None), PriorAuthModel.termdate >= today),
    )


def _person_code_clause(person_code: str):
    padded = (
        literal(",").concat(func.coalesce(PriorAuthModel.personcodes, "")).concat(",")
    )
    return padded.like(f"%,{person_code},%")


class PriorAuthRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_authnum(self, authnum: Decimal) -> PriorAuthModel | None:
        stmt = select(PriorAuthModel).where(PriorAuthModel.authnum == authnum)
        result = await self._session.execute(stmt)
        return result.scalars().first()

    async def next_authnum(self) -> Decimal:
        stmt = select(func.max(PriorAuthModel.authnum))
        highest = (await self._session.execute(stmt)).scalar_one_or_none()
        return Decimal(1) if highest is None else Decimal(highest) + 1

    async def search(
        self,
        pa_id: str | None = None,
        insured_id: str | None = None,
        person_code: str | None = None,
        subscriber_num: str | None = None,
        drug_name: str | None = None,
        ndc: str | None = None,
        status: PAStatus | None = None,
        eff_date: date | None = None,
        term_date: date | None = None,
        eff_date_from: date | None = None,
        eff_date_to: date | None = None,
        prescriber_npi: str | None = None,
        today: date | None = None,
        page: int = 1,
        page_size: int = 20,
        sort_by: str | None = None,
        sort_dir: str = "asc",
    ) -> tuple[Sequence[PriorAuthModel], int]:
        today = today or date.today()
        stmt = select(PriorAuthModel)

        if pa_id:
            stmt = stmt.where(cast(PriorAuthModel.authnum, String).like(f"%{pa_id}%"))
        if insured_id:
            stmt = stmt.where(PriorAuthModel.subscribernum.ilike(insured_id))
        # if person_code:
        #     stmt = stmt.where(_person_code_clause(person_code))
        if subscriber_num:
            stmt = stmt.where(PriorAuthModel.subscribernum.ilike(f"%{subscriber_num}%"))
        if drug_name:
            stmt = stmt.where(_drug_name_clause(drug_name))
        if ndc:
            stmt = stmt.where(PriorAuthModel.ndc == ndc)
        if eff_date:
            stmt = stmt.where(PriorAuthModel.effdate == eff_date)
        if term_date:
            stmt = stmt.where(PriorAuthModel.termdate == term_date)
        if prescriber_npi:
            stmt = stmt.where(PriorAuthModel.prescriberid == prescriber_npi)
        # if status:
        #     stmt = stmt.where(_status_clause(status, today))
        # if eff_date_from:
        #     stmt = stmt.where(PriorAuthModel.effdate >= eff_date_from)
        # if eff_date_to:
        #     stmt = stmt.where(PriorAuthModel.effdate <= eff_date_to)

        return await self._paginate(stmt, page, page_size, sort_by, sort_dir)

    async def add(self, prior_auth: PriorAuthModel) -> PriorAuthModel:
        self._session.add(prior_auth)
        await self._session.flush()
        return prior_auth

    async def _paginate(
        self,
        stmt,
        page: int,
        page_size: int,
        sort_by: str | None,
        sort_dir: str,
    ) -> tuple[Sequence[PriorAuthModel], int]:
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await self._session.execute(count_stmt)).scalar_one()

        sort_column = _SORTABLE_COLUMNS.get(sort_by, _DEFAULT_SORT_COLUMN)
        order_fn = desc if str(sort_dir).lower() == "desc" else asc
        stmt = stmt.order_by(order_fn(sort_column), asc(PriorAuthModel.authnum))

        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        result = await self._session.execute(stmt)
        return result.unique().scalars().all(), total


def _drug_name_clause(drug_name: str):
    pattern = f"%{drug_name}%"
    return or_(
        PriorAuthModel.genname.ilike(pattern),
        PriorAuthModel.manualgenname.ilike(pattern),
        PriorAuthModel.ndc.in_(
            select(DrugModel.ndc).where(DrugModel.drug_name.ilike(pattern))
        ),
    )
