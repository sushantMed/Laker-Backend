from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.permission_model import UserPermissionModel


class PermissionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_user_grants(self, user_id: UUID) -> list[tuple[str, int, int]]:
        """The screen grants held by a user — the equivalent of the legacy

            SELECT pername, viewperm, saveperm
              FROM sql.userperm p, sql.usermaster u
             WHERE u.username = :username AND u.userkey = p.userkey

        except that the join is on our own users.id rather than userkey.
        """
        result = await self.session.execute(
            select(
                UserPermissionModel.pername,
                UserPermissionModel.viewperm,
                UserPermissionModel.saveperm,
            ).where(UserPermissionModel.user_id == user_id)
        )
        return [tuple(row) for row in result.all()]
