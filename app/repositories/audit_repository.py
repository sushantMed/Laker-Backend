from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.upd_tran_model import UpdTranDetailModel, UpdTranModel

# UPDTRAN.USERID is 15 wide -- longer actors are truncated rather than rejected,
# same as the PA audit columns.
_USERID_MAX = 15
_DETAILKEY_MAX = 35
_FIELDNAME_MAX = 20
_UPDTABLE_MAX = 25
_VALUE_MAX = 200


class FieldChange:
    """One old -> new field change to record on an audit transaction."""

    def __init__(
        self,
        *,
        detail_key: str,
        upd_table: str,
        field_name: str,
        old_value: str | None,
        new_value: str | None,
    ) -> None:
        self.detail_key = detail_key
        self.upd_table = upd_table
        self.field_name = field_name
        self.old_value = old_value
        self.new_value = new_value


def _clip(value: str | None, limit: int) -> str | None:
    return value[:limit] if value else value


class AuditRepository:
    """Writes the legacy change log (SQLMGR.UPDTRAN / UPDTRANDETAIL)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def next_trankey(self) -> Decimal:
        stmt = select(func.max(UpdTranModel.trankey))
        highest = (await self._session.execute(stmt)).scalar_one_or_none()
        return Decimal(1) if highest is None else Decimal(highest) + 1

    async def record(
        self,
        *,
        client_code: str | None,
        tran_id: int,
        screen_id: int,
        screen_key: str,
        user_id: str | None,
        changes: Sequence[FieldChange],
        when: datetime | None = None,
    ) -> UpdTranModel:
        """Log one transaction header plus a detail row per changed field."""
        transaction = UpdTranModel(
            trankey=await self.next_trankey(),
            clientcode=client_code,
            tranid=Decimal(tran_id),
            screenid=Decimal(screen_id),
            screenkey=_clip(screen_key, 50),
            userid=_clip(user_id, _USERID_MAX),
            trants=when or datetime.now(),
        )
        self._session.add(transaction)

        for line_num, change in enumerate(changes, start=1):
            self._session.add(
                UpdTranDetailModel(
                    trankey=transaction.trankey,
                    linenum=Decimal(line_num),
                    detailkey=_clip(change.detail_key, _DETAILKEY_MAX),
                    updtable=_clip(change.upd_table, _UPDTABLE_MAX),
                    fieldname=_clip(change.field_name, _FIELDNAME_MAX),
                    oldvalue=_clip(change.old_value, _VALUE_MAX),
                    newvalue=_clip(change.new_value, _VALUE_MAX),
                )
            )

        await self._session.flush()
        return transaction
