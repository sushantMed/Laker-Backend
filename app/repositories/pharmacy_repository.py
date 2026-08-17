from __future__ import annotations

import math

from sqlalchemy import func, select, true

from app.models.pharmacy_model import PharmacyModel
from app.repositories.base_repository import BaseRepository
from app.schemas.pharmacy_schema import PharmacySearch

EQUATOR_LAT_MILE = 69.172
EARTH_RADIUS_MILES = 3963


def _compute_bounding_box(
    latitude: float, longitude: float, miles: float
) -> tuple[float, float, float, float]:
    max_lat = latitude + miles / EQUATOR_LAT_MILE
    min_lat = latitude - (max_lat - latitude)
    max_long = longitude + miles / (math.cos(math.radians(min_lat)) * EQUATOR_LAT_MILE)
    min_long = longitude - (max_long - longitude)
    return min_lat, max_lat, min_long, max_long


def _haversine_miles(lat1: float, long1: float, lat2: float, long2: float) -> float:
    if lat1 == lat2 and long1 == long2:
        return 0.0
    lat1, long1, lat2, long2 = map(math.radians, (lat1, long1, lat2, long2))
    cos_angle = math.sin(lat1) * math.sin(lat2) + math.cos(lat1) * math.cos(
        lat2
    ) * math.cos(long2 - long1)
    cos_angle = max(-1.0, min(1.0, cos_angle))  # guard float rounding past [-1, 1]
    return EARTH_RADIUS_MILES * math.acos(cos_angle)


class PharmacyRepository(BaseRepository[PharmacyModel]):
    model = PharmacyModel

    async def get_by_nabp(self, nabp: str) -> list[PharmacyModel]:
        stmt = select(PharmacyModel).where(
            PharmacyModel.nabp.ilike(f"{nabp}%"),
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_by_npi(self, npi: str) -> list[PharmacyModel]:
        stmt = select(PharmacyModel).where(
            PharmacyModel.npi.ilike(f"{npi}%"),
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_by_zip_code(
        self, zip_code: str, radius: int | None = None, is_24hr: bool = False
    ) -> list[PharmacyModel]:
        radius = radius or 10

        center_stmt = select(
            func.avg(PharmacyModel.latitude), func.avg(PharmacyModel.longitude)
        ).where(
            PharmacyModel.zip == zip_code,
            PharmacyModel.latitude.is_not(None),
            PharmacyModel.longitude.is_not(None),
        )
        center_result = await self.session.execute(center_stmt)
        center_row = center_result.first()
        if center_row is None or center_row[0] is None or center_row[1] is None:
            return []  # no geocoded pharmacy for this zip to anchor the search

        latitude = float(center_row[0])
        longitude = float(center_row[1])

        # 2. Bounding box as a cheap SQL pre-filter
        min_lat, max_lat, min_long, max_long = _compute_bounding_box(
            latitude, longitude, radius
        )
        filters = [
            PharmacyModel.latitude.is_not(None),
            PharmacyModel.longitude.is_not(None),
            PharmacyModel.latitude >= min_lat,
            PharmacyModel.latitude <= max_lat,
            PharmacyModel.longitude >= min_long,
            PharmacyModel.longitude <= max_long,
        ]

        if is_24hr:
            # Oracle does not support SQLAlchemy's ``IS 1`` boolean form.
            filters.append(PharmacyModel.is_24_hour == true())

        stmt = select(PharmacyModel).where(*filters)
        result = await self.session.execute(stmt)
        candidates = result.scalars().all()

        in_range: list[tuple[float, PharmacyModel]] = []
        for pharmacy in candidates:
            distance = _haversine_miles(
                latitude, longitude, float(pharmacy.latitude), float(pharmacy.longitude)
            )
            if distance <= radius:
                in_range.append((distance, pharmacy))

        # Sort nearest-first
        in_range.sort(key=lambda pair: pair[0])
        return [pharmacy for _, pharmacy in in_range]

    async def search(
        self,
        criteria: PharmacySearch,
        *,
        page: int,
        page_size: int,
        sort_by: str,
        sort_dir: str,
    ) -> tuple[list[PharmacyModel], int]:
        stmt = select(PharmacyModel)

        if criteria.name:
            stmt = stmt.where(PharmacyModel.pharmacy_name.ilike(f"%{criteria.name}%"))
        if criteria.nabp:
            stmt = stmt.where(PharmacyModel.nabp.ilike(f"%{criteria.nabp}%"))
        if criteria.npi:
            stmt = stmt.where(PharmacyModel.npi.ilike(f"%{criteria.npi}%"))
        if criteria.city:
            stmt = stmt.where(PharmacyModel.city.ilike(f"%{criteria.city}%"))
        if criteria.state:
            stmt = stmt.where(PharmacyModel.state.ilike(criteria.state))
        if criteria.zip_code:
            stmt = stmt.where(PharmacyModel.zip.ilike(f"{criteria.zip_code}%"))
        if criteria.is_24_hour is not None:
            stmt = stmt.where(PharmacyModel.is_24_hour == criteria.is_24_hour)

        return await self.paginate(
            stmt,
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            sort_dir=sort_dir,
        )
