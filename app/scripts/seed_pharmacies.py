"""
Seed pharmacies (lookup table) from pharmacies_seed.json.
Safe to run on application startup, and safe to run multiple times.

Behavior:
- New pharmacies (matched by npi) are inserted.
- Existing pharmacies are otherwise left untouched, EXCEPT that a NULL
  latitude/longitude is backfilled from the seed data if the seed record
  has coordinates. This lets re-running the seed populate geocoding for
  pharmacies that were inserted before coordinates existed in the seed
  file, without clobbering any other field.
- Each insert happens in its own SAVEPOINT, so a single bad/rejected
  record (e.g. a DB constraint violation) does not roll back the other
  valid records in the same run.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from sqlalchemy import select

from app.database.session import AsyncSessionLocal
from app.models.pharmacy_model import PharmacyModel

_DEFAULT_SEED_FILE = Path(__file__).resolve().parent / "pharmacies_seed.json"

# Natural-key column name used to detect duplicates/existing rows.
_PHARMACY_KEY = "npi"


def load_seed_data(json_path: Path = _DEFAULT_SEED_FILE) -> dict:
    with open(json_path, encoding="utf-8") as file:
        content = file.read()

    if not content.strip():
        raise ValueError(f"{json_path} is empty")

    return json.loads(content)


async def _seed_pharmacies(session, pharmacies_data: list[dict]) -> None:
    print("Seeding pharmacies...")

    existing_by_key: dict[str, PharmacyModel] = {
        pharmacy.npi: pharmacy
        for pharmacy in (await session.execute(select(PharmacyModel))).scalars().all()
    }

    inserted = 0
    updated = 0
    skipped_duplicate = 0
    skipped_malformed = 0
    skipped_db_error = 0

    for pharmacy_data in pharmacies_data:
        key = pharmacy_data.get(_PHARMACY_KEY)
        if not key:
            print(
                f"Skipping malformed pharmacy record, missing '{_PHARMACY_KEY}': {pharmacy_data}"
            )
            skipped_malformed += 1
            continue

        existing_pharmacy = existing_by_key.get(key)
        if existing_pharmacy is not None:
            backfilled = False
            if (
                existing_pharmacy.latitude is None
                and pharmacy_data.get("latitude") is not None
            ):
                existing_pharmacy.latitude = pharmacy_data["latitude"]
                backfilled = True
            if (
                existing_pharmacy.longitude is None
                and pharmacy_data.get("longitude") is not None
            ):
                existing_pharmacy.longitude = pharmacy_data["longitude"]
                backfilled = True

            if backfilled:
                updated += 1
            else:
                skipped_duplicate += 1
            continue

        try:
            async with session.begin_nested():
                session.add(PharmacyModel(**pharmacy_data))
            existing_by_key[key] = (
                None  # only need presence for later rows in this batch
            )
            inserted += 1
        except Exception as e:
            print(f"Failed to insert pharmacy '{key}': {e}")
            skipped_db_error += 1
            continue

    print(
        f"{inserted} new pharmacy(s) inserted, {updated} existing pharmacy(s) "
        f"backfilled with lat/long. Skipped {skipped_duplicate} unchanged "
        f"duplicate(s), {skipped_malformed} malformed record(s), "
        f"{skipped_db_error} DB-rejected record(s)."
    )


async def seed_pharmacies() -> None:
    """
    Seed pharmacies.

    Safe to run multiple times. New records (matched by npi) are inserted;
    existing records only get their lat/long backfilled if missing.
    """
    data = load_seed_data()

    async with AsyncSessionLocal() as session:
        await _seed_pharmacies(session, data.get("pharmacies", []))
        await session.flush()

        await session.commit()
        print("Pharmacies seeded successfully")


if __name__ == "__main__":
    asyncio.run(seed_pharmacies())
