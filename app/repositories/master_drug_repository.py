from __future__ import annotations

from collections.abc import Iterable, Sequence

from sqlalchemy import func, or_, select

from app.models.master_drug_model import MasterDrugModel
from app.repositories.base_repository import BaseRepository

# A keyed NDC this short is a labeler+product code without the package suffix,
# so it stands for every 11-character NDC beginning with it.
NDC_PREFIX_LENGTH = 9

# Oracle caps an IN list at 1000 expressions; stay well under it, and keep the
# OR'd LIKE list to the same size so a wide page still costs few round trips.
_CHUNK = 500


def _chunks(values: Sequence[str], size: int = _CHUNK) -> Iterable[Sequence[str]]:
    for start in range(0, len(values), size):
        yield values[start : start + size]


class MasterDrugRepository(BaseRepository[MasterDrugModel]):
    model = MasterDrugModel

    async def prod_desc_by_ndc(self, ndcs: Sequence[str]) -> dict[str, str]:
        """Product description for each full NDC, keyed by NDC."""
        if not ndcs:
            return {}

        found: dict[str, str] = {}
        for chunk in _chunks(list(ndcs)):
            stmt = select(
                MasterDrugModel.ndcupchri, MasterDrugModel.proddescabbrev
            ).where(MasterDrugModel.ndcupchri.in_(list(chunk)))
            for ndc, description in (await self.session.execute(stmt)).all():
                if ndc and description:
                    found[ndc] = description
        return found

    async def top_gpi_gen_name_by_ndc_prefix(
        self, prefixes: Sequence[str]
    ) -> dict[str, str]:
        """Generic name for each 9-character NDC, keyed by prefix.

        A short NDC covers a run of packages that need not agree on a GPI, so
        the winner is the (gpigenname, gpi) pair carried by the most rows under
        the prefix -- ties broken by name for a stable answer.
        """
        if not prefixes:
            return {}

        prefix_col = func.substr(MasterDrugModel.ndcupchri, 1, NDC_PREFIX_LENGTH)
        counted = func.count().label("cnt")

        # prefix -> (count, gpigenname) of the leader so far
        best: dict[str, tuple[int, str]] = {}
        for chunk in _chunks(list(prefixes)):
            stmt = (
                select(
                    prefix_col.label("prefix"),
                    MasterDrugModel.gpigenname,
                    MasterDrugModel.gpi,
                    counted,
                )
                .where(
                    or_(
                        *[
                            MasterDrugModel.ndcupchri.startswith(p, autoescape=True)
                            for p in chunk
                        ]
                    )
                )
                .group_by(prefix_col, MasterDrugModel.gpigenname, MasterDrugModel.gpi)
            )
            for prefix, gen_name, _gpi, count in (
                await self.session.execute(stmt)
            ).all():
                if not prefix or not gen_name:
                    continue
                current = best.get(prefix)
                if current is None or (count, gen_name) > current:
                    best[prefix] = (count, gen_name)

        return {prefix: gen_name for prefix, (_count, gen_name) in best.items()}
