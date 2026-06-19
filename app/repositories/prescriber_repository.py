from typing import Optional
from sqlalchemy import select


class PrescriberRepository:
    def __init__(self, session) -> None:
        self._session = session

    async def get_by_npi(self, npi: str):
        pass