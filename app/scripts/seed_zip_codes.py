"""
Seed the ZIPCODES reference table from zip_codes_seed.json.
Safe to run on application startup, and safe to run multiple times.

Behavior:
- Only ZIPs that don't already exist in the DB (matched by ZIP) are
  inserted. Existing rows are skipped, not re-inserted or updated.
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
from app.models.zip_code_model import ZipCodeModel

_DEFAULT_SEED_FILE = Path(__file__).resolve().parent / "zip_codes_seed.json"

# Natural-key column name used to detect duplicates.
_ZIP_KEY = "zip"


def load_seed_data(json_path: Path = _DEFAULT_SEED_FILE) -> dict:
    with open(json_path, encoding="utf-8") as file:
        content = file.read()

    if not content.strip():
        raise ValueError(f"{json_path} is empty")

    return json.loads(content)


async def _seed_zip_codes(session, zip_codes_data: list[dict]) -> None:
    print("Seeding zip codes...")

    existing_keys = set(
        (await session.execute(select(getattr(ZipCodeModel, _ZIP_KEY)))).scalars().all()
    )

    inserted = 0
    skipped_duplicate = 0
    skipped_malformed = 0
    skipped_db_error = 0

    for zip_code_data in zip_codes_data:
        key = zip_code_data.get(_ZIP_KEY)
        if not key:
            print(
                f"Skipping malformed zip code record, missing '{_ZIP_KEY}': {zip_code_data}"
            )
            skipped_malformed += 1
            continue

        if key in existing_keys:
            skipped_duplicate += 1
            continue

        try:
            async with session.begin_nested():
                session.add(ZipCodeModel(**zip_code_data))
            existing_keys.add(key)
            inserted += 1
        except Exception as e:
            print(f"Failed to insert zip code '{key}': {e}")
            skipped_db_error += 1
            continue

    print(
        f"{inserted} new zip code(s) inserted. "
        f"Skipped {skipped_duplicate} duplicate(s), "
        f"{skipped_malformed} malformed record(s), "
        f"{skipped_db_error} DB-rejected record(s)."
    )


async def seed_zip_codes() -> None:
    """
    Seed zip codes.

    Safe to run multiple times. Only ZIPs that don't already exist are
    inserted; existing rows are left untouched.
    """
    data = load_seed_data()

    async with AsyncSessionLocal() as session:
        await _seed_zip_codes(session, data.get("zip_codes", []))
        await session.flush()

        await session.commit()
        print("Zip codes seeded successfully")


if __name__ == "__main__":
    asyncio.run(seed_zip_codes())
