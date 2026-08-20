from __future__ import annotations

from collections.abc import Sequence
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    DrugNotFoundException,
    InvalidStatusTransitionException,
    MemberNotFoundException,
    PrescriberNotFoundException,
    PriorAuthNotEditableException,
    PriorAuthNotFoundException,
)
from app.models.drug_model import DrugModel
from app.models.member_model import MemberModel
from app.models.prescriber_model import PrescriberModel
from app.models.prior_auth_model import PriorAuthModel
from app.repositories.drug_repository import DrugRepository
from app.repositories.gpi_repository import GpiRepository
from app.repositories.master_drug_repository import (
    NDC_PREFIX_LENGTH,
    MasterDrugRepository,
)
from app.repositories.member_repository import MemberRepository
from app.repositories.prescriber_repository import PrescriberRepository
from app.repositories.prior_auth_repository import PriorAuthRepository
from app.schemas.prior_auth_schema import (
    CreatePARequest,
    PAByEntityQuery,
    PADetail,
    PAMemberSearchResult,
    PASearchRequest,
    PASearchRequestByMemberPath,
    PASearchResult,
    PatchPARequest,
    UpdatePARequest,
)
from app.utils.enums import PAStatus, derive_pa_status, pa_action_for_status
from app.utils.pagination import PagedResponse

_ALLOWED_TRANSITIONS: dict[PAStatus, set[PAStatus]] = {
    PAStatus.PENDING: {PAStatus.AUTHORIZED, PAStatus.DECLINED, PAStatus.EXPIRED},
    PAStatus.AUTHORIZED: {PAStatus.DECLINED, PAStatus.EXPIRED},
    PAStatus.DECLINED: {PAStatus.AUTHORIZED},
    PAStatus.EXPIRED: set(),
}

_AUDIT_USER_MAX = 20

# A GPI recorded as a compound stands for no single drug, so no name is bound.
_COMPOUND_GPI = "COMPOUND"
_FULL_GPI_LENGTH = 14


class _References:
    def __init__(
        self,
        members: Sequence[MemberModel],
        drugs: Sequence[DrugModel],
        prescribers: Sequence[PrescriberModel],
    ) -> None:
        self._members_by_insured_id: dict[str, list[MemberModel]] = {}
        for member in members:
            if member.insured_id:
                self._members_by_insured_id.setdefault(member.insured_id, []).append(
                    member
                )
        self._drugs_by_ndc = {drug.ndc: drug for drug in drugs}
        self._prescribers_by_npi = {p.npi: p for p in prescribers}

    @classmethod
    def empty(cls) -> _References:
        return cls([], [], [])

    def member_for(self, prior_auth: PriorAuthModel) -> MemberModel | None:
        if not prior_auth.subscribernum:
            return None

        candidates = self._members_by_insured_id.get(prior_auth.subscribernum, [])
        if not candidates:
            return None

        codes = _person_codes(prior_auth.personcodes)
        if not codes:
            return min(candidates, key=lambda m: m.person_code or "")

        matches = [m for m in candidates if m.person_code in codes]
        if not matches:
            return None
        return min(matches, key=lambda m: m.person_code or "")

    def drug_for(self, prior_auth: PriorAuthModel) -> DrugModel | None:
        return self._drugs_by_ndc.get(prior_auth.ndc) if prior_auth.ndc else None

    def prescriber_for(self, prior_auth: PriorAuthModel) -> PrescriberModel | None:
        if not prior_auth.prescriberid:
            return None
        return self._prescribers_by_npi.get(prior_auth.prescriberid)


def _clean(value: str | None) -> str | None:
    """Legacy columns are fixed-width, so a keyed value can arrive padded."""
    if value is None:
        return None
    return value.strip() or None


def _is_compound_gpi(gpi: str) -> bool:
    return gpi.upper() == _COMPOUND_GPI


class _DrugNames:
    """Drug names for one page of PAs, resolved from the reference tables.

    Where a reference table holds nothing for the PA's NDC or GPI, the name the
    PA itself carries stands in -- the grid keeps showing what it showed before
    MASTERDRUG was in the picture.
    """

    def __init__(
        self,
        ndc_prefix_names: dict[str, str],
        ndc_names: dict[str, str],
        gpi_names: dict[str, str],
    ) -> None:
        self._ndc_prefix_names = ndc_prefix_names
        self._ndc_names = ndc_names
        self._gpi_names = gpi_names

    @classmethod
    def empty(cls) -> _DrugNames:
        return cls({}, {}, {})

    def for_ndc(self, prior_auth: PriorAuthModel) -> str | None:
        ndc = _clean(prior_auth.ndc)
        if not ndc:
            return None

        if len(ndc) == NDC_PREFIX_LENGTH:
            name = self._ndc_prefix_names.get(ndc)
        else:
            name = self._ndc_names.get(ndc)
        return name or _drug_name_for_ndc(prior_auth)

    def for_gpi(self, prior_auth: PriorAuthModel) -> str | None:
        gpi = _clean(prior_auth.gpi)
        if not gpi or _is_compound_gpi(gpi):
            return None
        return self._gpi_names.get(gpi) or _drug_name_for_gpi(prior_auth)


def _person_codes(personcodes: str | None) -> set[str]:
    if not personcodes:
        return set()
    return {code.strip() for code in personcodes.split(",") if code.strip()}


def _format_pa_id(authnum: Decimal | None) -> str:
    if authnum is None:
        return ""
    return str(int(authnum))


def _parse_pa_id(pa_id: str) -> Decimal | None:
    try:
        return Decimal(pa_id.strip())
    except (InvalidOperation, AttributeError, ValueError):
        return None


def _drug_name(prior_auth: PriorAuthModel, drug: DrugModel | None) -> str | None:
    if drug:
        return drug.drug_name
    return prior_auth.manualgenname or prior_auth.genname


def _drug_name_for_ndc(prior_auth: PriorAuthModel) -> str | None:
    """Name of the NDC-specific drug as recorded on the PA itself."""
    if not prior_auth.ndc:
        return None
    return prior_auth.manualgenname or prior_auth.genname


def _drug_name_for_gpi(prior_auth: PriorAuthModel) -> str | None:
    """Generic name standing in for the PA's GPI class."""
    if not prior_auth.gpi:
        return None
    return prior_auth.genname or prior_auth.manualgenname


def _provider(
    prior_auth: PriorAuthModel, prescriber: PrescriberModel | None
) -> str | None:
    if prescriber:
        return prescriber.name
    return prior_auth.authby


def _to_int(value: Decimal | None) -> int | None:
    return int(value) if value is not None else None


def _to_search_result(
    prior_auth: PriorAuthModel, refs: _References, today: date
) -> PASearchResult:
    member = refs.member_for(prior_auth)
    return PASearchResult(
        pa_id=_format_pa_id(prior_auth.authnum),
        member_id=member.member_id if member else None,
        first_name=member.first_name if member else None,
        last_name=member.last_name if member else None,
        drug_name=_drug_name(prior_auth, refs.drug_for(prior_auth)),
        ndc=prior_auth.ndc,
        provider=_provider(prior_auth, refs.prescriber_for(prior_auth)),
        eff_date=prior_auth.effdate,
        term_date=prior_auth.termdate,
        status=derive_pa_status(
            prior_auth.action, prior_auth.denial, prior_auth.termdate, today
        ),
    )


def _to_member_search_result(
    prior_auth: PriorAuthModel, names: _DrugNames
) -> PAMemberSearchResult:
    return PAMemberSearchResult(
        auth_num=_format_pa_id(prior_auth.authnum),
        ndc=prior_auth.ndc,
        gpi=prior_auth.gpi,
        drug_name_ndc=names.for_ndc(prior_auth),
        drug_name_gpi=names.for_gpi(prior_auth),
        action=prior_auth.action,
        eff_date=prior_auth.effdate,
        term_date=prior_auth.termdate,
        last_user=prior_auth.changeuser,
        subscriber_num=prior_auth.subscribernum,
        person_codes=prior_auth.personcodes,
    )


def _to_detail(prior_auth: PriorAuthModel, refs: _References, today: date) -> PADetail:
    member = refs.member_for(prior_auth)
    drug = refs.drug_for(prior_auth)
    return PADetail(
        pa_id=_format_pa_id(prior_auth.authnum),
        member_id=member.member_id if member else None,
        first_name=member.first_name if member else None,
        last_name=member.last_name if member else None,
        drug_name=_drug_name(prior_auth, drug),
        ndc=prior_auth.ndc,
        provider=_provider(prior_auth, refs.prescriber_for(prior_auth)),
        eff_date=prior_auth.effdate,
        term_date=prior_auth.termdate,
        status=derive_pa_status(
            prior_auth.action, prior_auth.denial, prior_auth.termdate, today
        ),
        gpi=prior_auth.gpi,
        group_number=prior_auth.groupnum,
        person_codes=prior_auth.personcodes,
        prescriber_npi=prior_auth.prescriberid,
        pharmacy_nabp=prior_auth.providerid,
        brand_generic=prior_auth.bg,
        diagnosis=prior_auth.diagnosis,
        second_diagnosis=prior_auth.seconddiagnosis,
        dea_class=prior_auth.deaclass,
        reason_code=prior_auth.reasoncode,
        notes=prior_auth.notes,
        message=prior_auth.message,
        refills=prior_auth.refills,
        max_daily_dose=prior_auth.maxdailydose,
        max_script_qty=prior_auth.maxscriptqty,
        max_script_days=prior_auth.maxscriptdays,
        max_scripts=_to_int(prior_auth.maxscripts),
        source=prior_auth.source,
        auth_by=prior_auth.authby,
        called_in_by=prior_auth.calledinby,
        appeal=prior_auth.appeal,
        denial=prior_auth.denial,
        request_received=prior_auth.reqreceived,
        documentation_received=prior_auth.documentation,
        request_approved=prior_auth.reqapproved,
        member_notified=prior_auth.memnotified,
        days_old=_to_int(prior_auth.daysold),
        created_by=prior_auth.createuser,
        created_at=prior_auth.createts,
        changed_by=prior_auth.changeuser,
        changed_at=prior_auth.changets,
    )


class PriorAuthService:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = PriorAuthRepository(session)
        self._member_repo = MemberRepository(session)
        self._drug_repo = DrugRepository(session)
        self._master_drug_repo = MasterDrugRepository(session)
        self._gpi_repo = GpiRepository(session)
        self._prescriber_repo = PrescriberRepository(session)
        self._session = session

    async def get_prior_auth(self, pa_id: str) -> PADetail:
        prior_auth = await self._require_prior_auth(pa_id)
        refs = await self._load_references([prior_auth])
        return _to_detail(prior_auth, refs, date.today())

    async def search_prior_auths(
        self, request: PASearchRequest
    ) -> PagedResponse[PASearchResult]:
        criteria = request.searchRequest

        insured_id: str | None = None
        person_code: str | None = None
        subscriber_num: str | None = None
        if criteria.member_id:
            member = await self._member_repo.get_by_member_id(criteria.member_id)
            if member:
                insured_id = member.insured_id
                person_code = member.person_code
            else:
                subscriber_num = criteria.member_id

        items, total = await self._repo.search(
            pa_id=criteria.pa_id,
            insured_id=insured_id,
            person_code=person_code,
            subscriber_num=subscriber_num,
            drug_name=criteria.drug_name,
            ndc=criteria.ndc,
            status=criteria.status,
            eff_date_from=criteria.eff_date_from,
            eff_date_to=criteria.eff_date_to,
            page=request.pagination.page,
            page_size=request.pagination.page_size,
            sort_by=request.sort.sort_by,
            sort_dir=request.sort.sort_dir,
        )

        return await self._to_page(
            items, total, request.pagination.page, request.pagination.page_size
        )

    async def search_prior_auths_for_member(
        self, member_id: str, request: PASearchRequestByMemberPath
    ) -> PagedResponse[PAMemberSearchResult]:
        member = await self._require_member(member_id)
        criteria = request.searchRequest

        if not member.insured_id:
            return PagedResponse.of(
                data=[],
                page=request.pagination.page,
                page_size=request.pagination.page_size,
                total=0,
            )

        items, total = await self._repo.search(
            subscriber_num=member.insured_id,
            person_code=member.person_code,
            ndc=criteria.ndc,
            # effDate is the older name for the lower bound; both are floors, so
            # passing both simply ANDs them and the later one wins.
            eff_date=criteria.eff_date,
            eff_date_from=criteria.eff_date_from,
            eff_date_to=criteria.eff_date_to,
            # term_date=criteria.term_date,
            page=request.pagination.page,
            page_size=request.pagination.page_size,
            sort_by=request.sort.sort_by,
            sort_dir=request.sort.sort_dir,
        )

        # The member is already known from the path, so only the drug names are
        # looked up -- no member or prescriber resolution.
        names = await self._load_drug_names(items)
        return PagedResponse.of(
            data=[_to_member_search_result(pa, names) for pa in items],
            page=request.pagination.page,
            page_size=request.pagination.page_size,
            total=total,
        )

    async def get_prior_auths_for_member(
        self, member_id: str, query: PAByEntityQuery
    ) -> PagedResponse[PASearchResult]:
        member = await self._require_member(member_id)
        items, total = await self._repo.search(
            insured_id=member.insured_id,
            person_code=member.person_code,
            status=query.status,
            page=query.page,
            page_size=query.page_size,
            sort_dir="desc",
        )
        return await self._to_page(items, total, query.page, query.page_size)

    async def get_prior_auths_for_drug(
        self, ndc: str, query: PAByEntityQuery
    ) -> PagedResponse[PASearchResult]:
        drug = await self._drug_repo.get_by_ndc(ndc)
        if not drug:
            raise DrugNotFoundException(f"Drug with NDC '{ndc}' not found.")

        items, total = await self._repo.search(
            ndc=ndc,
            status=query.status,
            page=query.page,
            page_size=query.page_size,
            sort_dir="desc",
        )
        return await self._to_page(items, total, query.page, query.page_size)

    async def get_prior_auths_for_prescriber(
        self, npi: str, query: PAByEntityQuery
    ) -> PagedResponse[PASearchResult]:
        prescriber = await self._prescriber_repo.get_by_npi(npi)
        if not prescriber:
            raise PrescriberNotFoundException(f"Prescriber '{npi}' not found.")

        items, total = await self._repo.search(
            prescriber_npi=npi,
            status=query.status,
            page=query.page,
            page_size=query.page_size,
            sort_dir="desc",
        )
        return await self._to_page(items, total, query.page, query.page_size)

    async def create_prior_auth(
        self, request: CreatePARequest, actor: str | None = None
    ) -> PADetail:
        member = await self._require_member(request.member_id, status_code=422)
        drug = await self._drug_repo.get_by_ndc(request.ndc)
        if not drug:
            raise DrugNotFoundException(f"Drug with NDC '{request.ndc}' not found.")

        term_date = request.term_date
        if request.status is PAStatus.EXPIRED:
            term_date = _expire_on_or_before(term_date)

        prior_auth = PriorAuthModel(
            authnum=await self._repo.next_authnum(),
            subscribernum=member.insured_id,
            groupnum=member.plan.group_number if member.plan else None,
            personcodes=member.person_code,
            effdate=request.eff_date,
            termdate=term_date,
            ndc=request.ndc,
            gpi=request.gpi or drug.gpi,
            manualgenname=request.drug_name,
            authby=request.provider,
            action=pa_action_for_status(request.status),
            reasoncode=request.reason_code,
            notes=request.notes,
            diagnosis=request.diagnosis,
            source="WEB",
            createuser=_audit_user(actor),
            createts=datetime.now(),
        )
        if request.status is PAStatus.AUTHORIZED:
            prior_auth.reqapproved = date.today()

        await self._repo.add(prior_auth)
        await self._session.commit()
        await self._session.refresh(prior_auth)

        refs = await self._load_references([prior_auth])
        return _to_detail(prior_auth, refs, date.today())

    async def update_prior_auth(
        self, pa_id: str, request: UpdatePARequest, actor: str | None = None
    ) -> PADetail:
        prior_auth = await self._require_prior_auth(pa_id)
        today = date.today()
        current = derive_pa_status(
            prior_auth.action, prior_auth.denial, prior_auth.termdate, today
        )
        if current is PAStatus.EXPIRED:
            raise PriorAuthNotEditableException(
                f"Prior authorization '{pa_id}' has expired and cannot be updated."
            )
        _require_valid_transition(current, request.status, pa_id)

        prior_auth.effdate = request.eff_date
        prior_auth.termdate = (
            _expire_on_or_before(request.term_date)
            if request.status is PAStatus.EXPIRED
            else request.term_date
        )
        prior_auth.ndc = request.ndc
        prior_auth.gpi = request.gpi
        prior_auth.manualgenname = request.drug_name
        prior_auth.authby = request.provider
        prior_auth.reasoncode = request.reason_code
        prior_auth.notes = request.notes
        prior_auth.diagnosis = request.diagnosis
        _apply_status(prior_auth, request.status, today)
        _stamp_change(prior_auth, actor)

        await self._session.commit()
        await self._session.refresh(prior_auth)

        refs = await self._load_references([prior_auth])
        return _to_detail(prior_auth, refs, today)

    async def patch_prior_auth(
        self, pa_id: str, request: PatchPARequest, actor: str | None = None
    ) -> PADetail:
        prior_auth = await self._require_prior_auth(pa_id)
        today = date.today()
        current = derive_pa_status(
            prior_auth.action, prior_auth.denial, prior_auth.termdate, today
        )
        if current is PAStatus.EXPIRED:
            raise PriorAuthNotEditableException(
                f"Prior authorization '{pa_id}' has expired and cannot be updated."
            )

        provided = request.model_fields_set

        if "status" in provided and request.status is not None:
            _require_valid_transition(current, request.status, pa_id)
            _apply_status(prior_auth, request.status, today)
        if "reason_code" in provided or "reasonCode" in provided:
            prior_auth.reasoncode = request.reason_code
        if "notes" in provided:
            prior_auth.notes = request.notes

        _stamp_change(prior_auth, actor)

        await self._session.commit()
        await self._session.refresh(prior_auth)

        refs = await self._load_references([prior_auth])
        return _to_detail(prior_auth, refs, today)

    async def _require_member(
        self, member_id: str, status_code: int = 404
    ) -> MemberModel:
        # A member id keyed with surrounding whitespace is the same member.
        member_id = _clean(member_id) or ""
        member = await self._member_repo.get_by_member_id(member_id)
        if not member:
            exc = MemberNotFoundException(f"Member '{member_id}' not found.")
            exc.status_code = status_code
            raise exc
        return member

    async def _require_prior_auth(self, pa_id: str) -> PriorAuthModel:
        authnum = _parse_pa_id(pa_id)
        if authnum is None:
            raise PriorAuthNotFoundException(
                f"Prior authorization '{pa_id}' not found."
            )

        prior_auth = await self._repo.get_by_authnum(authnum)
        if not prior_auth:
            raise PriorAuthNotFoundException(
                f"Prior authorization '{pa_id}' not found."
            )
        return prior_auth

    async def _load_references(
        self, prior_auths: Sequence[PriorAuthModel]
    ) -> _References:
        if not prior_auths:
            return _References.empty()

        insured_ids = {pa.subscribernum for pa in prior_auths if pa.subscribernum}
        ndcs = {pa.ndc for pa in prior_auths if pa.ndc}
        npis = {pa.prescriberid for pa in prior_auths if pa.prescriberid}

        return _References(
            members=await self._member_repo.get_by_insured_ids(sorted(insured_ids)),
            drugs=await self._drug_repo.get_by_ndcs(sorted(ndcs)),
            prescribers=await self._prescriber_repo.get_by_npis(sorted(npis)),
        )

    async def _load_drug_names(
        self, prior_auths: Sequence[PriorAuthModel]
    ) -> _DrugNames:
        """Resolve every NDC and GPI on the page in a handful of queries."""
        if not prior_auths:
            return _DrugNames.empty()

        ndcs = {ndc for pa in prior_auths if (ndc := _clean(pa.ndc))}
        prefixes = {ndc for ndc in ndcs if len(ndc) == NDC_PREFIX_LENGTH}

        gpis = {
            gpi
            for pa in prior_auths
            if (gpi := _clean(pa.gpi)) and not _is_compound_gpi(gpi)
        }
        full_gpis = {gpi for gpi in gpis if len(gpi) == _FULL_GPI_LENGTH}

        gpi_names = await self._gpi_repo.gen_names_by_gpi(sorted(full_gpis))
        gpi_names.update(
            await self._gpi_repo.names_by_partial_gpi(sorted(gpis - full_gpis))
        )

        return _DrugNames(
            ndc_prefix_names=await self._master_drug_repo.top_gpi_gen_name_by_ndc_prefix(
                sorted(prefixes)
            ),
            ndc_names=await self._master_drug_repo.prod_desc_by_ndc(
                sorted(ndcs - prefixes)
            ),
            gpi_names=gpi_names,
        )

    async def _to_page(
        self,
        items: Sequence[PriorAuthModel],
        total: int,
        page: int,
        page_size: int,
    ) -> PagedResponse[PASearchResult]:
        refs = await self._load_references(items)
        today = date.today()
        return PagedResponse.of(
            data=[_to_search_result(pa, refs, today) for pa in items],
            page=page,
            page_size=page_size,
            total=total,
        )


def _require_valid_transition(current: PAStatus, target: PAStatus, pa_id: str) -> None:
    if target is current:
        return
    if target not in _ALLOWED_TRANSITIONS[current]:
        raise InvalidStatusTransitionException(
            f"Prior authorization '{pa_id}' cannot move from "
            f"{current.value} to {target.value}."
        )


def _expire_on_or_before(term_date: date | None, today: date | None = None) -> date:
    today = today or date.today()
    yesterday = today - timedelta(days=1)
    if term_date and term_date < today:
        return term_date
    return yesterday


def _apply_status(prior_auth: PriorAuthModel, status: PAStatus, today: date) -> None:
    prior_auth.action = pa_action_for_status(status)

    if status is PAStatus.DECLINED:
        prior_auth.reqapproved = None
    else:
        prior_auth.denial = None

    if status is PAStatus.AUTHORIZED:
        prior_auth.reqapproved = prior_auth.reqapproved or today
    elif status is PAStatus.EXPIRED:
        prior_auth.termdate = _expire_on_or_before(prior_auth.termdate, today)
    elif status is PAStatus.PENDING:
        prior_auth.reqapproved = None


def _audit_user(actor: str | None) -> str | None:
    return actor[:_AUDIT_USER_MAX] if actor else None


def _stamp_change(prior_auth: PriorAuthModel, actor: str | None) -> None:
    prior_auth.changeuser = _audit_user(actor)
    prior_auth.changets = datetime.now()
