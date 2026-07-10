from sqlalchemy import exists, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.auth_model import RefreshTokenModel, RevokedAccessTokenModel
from app.models.user_model import UserModel


class AuthRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_user_by_email(self, email: str) -> UserModel | None:
        result = await self.session.execute(
            select(UserModel).where(func.lower(UserModel.email) == email.lower())
        )
        return result.scalar_one_or_none()

    async def get_user_by_id(self, user_id: int) -> UserModel | None:
        return await self.session.get(UserModel, user_id)

    async def save_refresh_token(self, token: RefreshTokenModel) -> RefreshTokenModel:
        self.session.add(token)
        await self.session.commit()
        await self.session.refresh(token)
        return token

    async def get_refresh_token(self, token: str) -> RefreshTokenModel | None:
        result = await self.session.execute(
            select(RefreshTokenModel).where(RefreshTokenModel.token == token)
        )
        return result.scalar_one_or_none()

    async def revoke_refresh_family(self, family_id: str) -> None:
        await self.session.execute(
            update(RefreshTokenModel)
            .where(RefreshTokenModel.family_id == family_id)
            .values(revoked=True)
        )
        await self.session.commit()

    async def revoke_user_refresh_tokens(self, user_id: int) -> None:
        await self.session.execute(
            update(RefreshTokenModel)
            .where(RefreshTokenModel.user_id == user_id)
            .values(revoked=True)
        )
        await self.session.commit()

    async def revoke_access_token(self, t_hash: str, expires_at) -> None:
        if await self.is_access_token_revoked(t_hash):
            return
        self.session.add(
            RevokedAccessTokenModel(token_hash=t_hash, expires_at=expires_at)
        )
        await self.session.commit()

    async def is_access_token_revoked(self, t_hash: str) -> bool:
        stmt = select(exists().where(RevokedAccessTokenModel.token_hash == t_hash))
        return await self.session.scalar(stmt)
