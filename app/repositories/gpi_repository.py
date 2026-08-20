from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.gpi_desc_model import GpiDescModel
from app.models.gpi_list_model import GpiListModel

# GpiList keys a partial GPI with a leading "G"; GpiDesc keys the full 14 as-is.
_PARTIAL_GPI_PREFIX = "G"


class GpiRepository:
    """Names for a GPI, from whichever of the two legacy tables holds it."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def gen_names_by_gpi(self, gpis: Sequence[str]) -> dict[str, str]:
        """GpiDesc.GPIGenName for each full 14-character GPI."""
        if not gpis:
            return {}

        stmt = select(GpiDescModel.gpi, GpiDescModel.gpigenname).where(
            GpiDescModel.gpi.in_(list(gpis))
        )
        return {
            gpi: name for gpi, name in (await self._session.execute(stmt)).all() if name
        }

    async def names_by_partial_gpi(self, gpis: Sequence[str]) -> dict[str, str]:
        """GpiList.Name for each partial GPI, keyed by the bare GPI.

        Callers pass the GPI as the PA carries it; the "G" the table keys on is
        added here and stripped back off the result.
        """
        if not gpis:
            return {}

        by_key = {f"{_PARTIAL_GPI_PREFIX}{gpi}": gpi for gpi in gpis}
        stmt = select(GpiListModel.gpi, GpiListModel.name).where(
            GpiListModel.gpi.in_(list(by_key))
        )
        return {
            by_key[key]: name
            for key, name in (await self._session.execute(stmt)).all()
            if name and key in by_key
        }
