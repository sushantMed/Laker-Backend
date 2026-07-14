"""
Seed drugs, pharmacies and prescribers (lookup tables) from a JSON file.
Safe to run on application startup, and safe to run multiple times.

Behavior:
- Only records that don't already exist in the DB (matched by their natural
  key: ndc for drugs, npi for pharmacies and prescribers) are inserted.
  Records that already exist are skipped, not re-inserted or updated.
- Each record is inserted in its own SAVEPOINT, so a single bad/rejected
  record (e.g. a DB constraint violation or bad enum value) does not roll
  back the other valid records in the same run.

NOTE: This assumes DrugModel's natural key column is `ndc`, and
PharmacyModel / PrescriberModel's natural key column is `npi`. Adjust the
`_DRUG_KEY` / `_PHARMACY_KEY` / `_PRESCRIBER_KEY` constants below if your
actual column names differ.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from sqlalchemy import select

from app.database.session import AsyncSessionLocal
from app.models.drug_model import DrugModel
from app.models.pharmacy_model import PharmacyModel
from app.models.prescriber_model import PrescriberModel
from app.utils.enums import BrandGeneric, Maintenance

_DEFAULT_SEED_FILE = Path(__file__).resolve().parent / "lookups_seed.json"

# Natural-key column names used to detect duplicates for each table.
# Change these if your models use different field names.
_DRUG_KEY = "ndc"
_PHARMACY_KEY = "npi"
_PRESCRIBER_KEY = "npi"


def load_seed_data(json_path: Path = _DEFAULT_SEED_FILE) -> dict:
    with open(json_path, encoding="utf-8") as file:
        content = file.read()

    if not content.strip():
        raise ValueError(f"{json_path} is empty")

    return json.loads(content)


async def _seed_drugs(session, drugs_data: list[dict]) -> None:
    print("Seeding drugs...")

    existing_keys = set(
        (await session.execute(select(getattr(DrugModel, _DRUG_KEY)))).scalars().all()
    )

    inserted = 0
    skipped_duplicate = 0
    skipped_malformed = 0
    skipped_db_error = 0

    for drug_data in drugs_data:
        key = drug_data.get(_DRUG_KEY)
        if not key:
            print(f"Skipping malformed drug record, missing '{_DRUG_KEY}': {drug_data}")
            skipped_malformed += 1
            continue

        if key in existing_keys:
            skipped_duplicate += 1
            continue

        try:
            drug_data = drug_data.copy()
            drug_data["brand_generic"] = BrandGeneric(drug_data["brand_generic"])
            drug_data["maintenance"] = Maintenance(drug_data["maintenance"])
        except (KeyError, ValueError) as e:
            print(f"Skipping malformed drug record '{key}': {e}")
            skipped_malformed += 1
            continue

        try:
            async with session.begin_nested():
                session.add(DrugModel(**drug_data))
            existing_keys.add(key)
            inserted += 1
        except Exception as e:
            print(f"Failed to insert drug '{key}': {e}")
            skipped_db_error += 1
            continue

    print(
        f"{inserted} new drug(s) inserted. "
        f"Skipped {skipped_duplicate} duplicate(s), "
        f"{skipped_malformed} malformed record(s), "
        f"{skipped_db_error} DB-rejected record(s)."
    )


async def _seed_pharmacies(session, pharmacies_data: list[dict]) -> None:
    print("Seeding pharmacies...")

    existing_keys = set(
        (await session.execute(select(getattr(PharmacyModel, _PHARMACY_KEY))))
        .scalars()
        .all()
    )

    inserted = 0
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

        if key in existing_keys:
            skipped_duplicate += 1
            continue

        try:
            async with session.begin_nested():
                session.add(PharmacyModel(**pharmacy_data))
            existing_keys.add(key)
            inserted += 1
        except Exception as e:
            print(f"Failed to insert pharmacy '{key}': {e}")
            skipped_db_error += 1
            continue

    print(
        f"{inserted} new pharmacy(s) inserted. "
        f"Skipped {skipped_duplicate} duplicate(s), "
        f"{skipped_malformed} malformed record(s), "
        f"{skipped_db_error} DB-rejected record(s)."
    )


async def _seed_prescribers(session, prescribers_data: list[dict]) -> None:
    print("Seeding prescribers...")

    existing_keys = set(
        (await session.execute(select(getattr(PrescriberModel, _PRESCRIBER_KEY))))
        .scalars()
        .all()
    )

    inserted = 0
    skipped_duplicate = 0
    skipped_malformed = 0
    skipped_db_error = 0

    for prescriber_data in prescribers_data:
        key = prescriber_data.get(_PRESCRIBER_KEY)
        if not key:
            print(
                f"Skipping malformed prescriber record, missing '{_PRESCRIBER_KEY}': {prescriber_data}"
            )
            skipped_malformed += 1
            continue

        if key in existing_keys:
            skipped_duplicate += 1
            continue

        try:
            async with session.begin_nested():
                session.add(PrescriberModel(**prescriber_data))
            existing_keys.add(key)
            inserted += 1
        except Exception as e:
            print(f"Failed to insert prescriber '{key}': {e}")
            skipped_db_error += 1
            continue

    print(f"{inserted} new prescriber(s) inserted. ")


async def seed_lookups() -> None:
    """
    Seed drugs, pharmacies and prescribers.

    Safe to run multiple times. Only records that don't already exist
    (matched by their natural key) are inserted; existing records are
    left untouched.
    """
    data = load_seed_data()

    async with AsyncSessionLocal() as session:
        await _seed_drugs(session, data.get("drugs", []))
        await session.flush()

        await _seed_pharmacies(session, data.get("pharmacies", []))
        await session.flush()

        await _seed_prescribers(session, data.get("prescribers", []))
        await session.flush()

        await session.commit()
        print("Lookups seeded successfully")


if __name__ == "__main__":
    asyncio.run(seed_lookups())
