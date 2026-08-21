"""
Seed the ZIPCODES reference table from zip_codes_seed.json.
Safe to run on application startup, and safe to run multiple times.

Behavior:
- New ZIPs (matched by zip) are inserted.
- Existing ZIPs are otherwise left untouched, EXCEPT that a NULL citytype
  is backfilled from the seed data if the seed record has one. CITYTYPE
  ='D' is required by PharmacyRepository.get_by_zip_code's network-eligible
  pharmacy match, so this lets re-running the seed populate it for ZIPs
  that were inserted before that filter existed, without clobbering any
  other field.
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

    existing_by_key: dict[str, ZipCodeModel] = {
        getattr(zip_code, _ZIP_KEY): zip_code
        for zip_code in (await session.execute(select(ZipCodeModel))).scalars().all()
    }

    inserted = 0
    updated = 0
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

        existing_zip_code = existing_by_key.get(key)
        if existing_zip_code is not None:
            if (
                existing_zip_code.citytype is None
                and zip_code_data.get("citytype") is not None
            ):
                existing_zip_code.citytype = zip_code_data["citytype"]
                updated += 1
            else:
                skipped_duplicate += 1
            continue

        try:
            async with session.begin_nested():
                session.add(ZipCodeModel(**zip_code_data))
            existing_by_key[key] = (
                None  # only need presence for later rows in this batch
            )
            inserted += 1
        except Exception as e:
            print(f"Failed to insert zip code '{key}': {e}")
            skipped_db_error += 1
            continue

    print(
        f"{inserted} new zip code(s) inserted, {updated} existing zip code(s) "
        f"backfilled with citytype. Skipped {skipped_duplicate} unchanged "
        f"duplicate(s), {skipped_malformed} malformed record(s), "
        f"{skipped_db_error} DB-rejected record(s)."
    )


async def seed_zip_codes() -> None:
    """
    Seed zip codes.

    Safe to run multiple times. New records (matched by zip) are inserted;
    existing records only get their citytype backfilled if missing.
    """
    data = load_seed_data()

    async with AsyncSessionLocal() as session:
        await _seed_zip_codes(session, data.get("zip_codes", []))
        await session.flush()

        await session.commit()
        print("Zip codes seeded successfully")


if __name__ == "__main__":
    asyncio.run(seed_zip_codes())
