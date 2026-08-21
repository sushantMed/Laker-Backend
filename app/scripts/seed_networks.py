"""
Seed the legacy NET / NETLIST reference tables from networks_seed.json.
Safe to run on application startup, and safe to run multiple times.

NETLIST rows gate which pharmacies are eligible for a zip-radius search --
see PharmacyRepository.get_by_zip_code -- so run this after seed_pharmacies
and seed_zip_codes if you want a fresh database's zip search to actually
return results.

Behavior:
- Only records that don't already exist in the DB (matched by their natural
  key -- see the _*_KEY tuples below) are inserted. Records that already
  exist are skipped, not re-inserted or updated.
- Each record is inserted in its own SAVEPOINT, so a single bad/rejected
  record (e.g. a DB constraint violation) does not roll back the other
  valid records in the same run.
"""

from __future__ import annotations

import asyncio
import json
from datetime import date
from pathlib import Path

from sqlalchemy import select

from app.database.session import AsyncSessionLocal
from app.models.net_model import NetModel
from app.models.netlist_model import NetListModel

_DEFAULT_SEED_FILE = Path(__file__).resolve().parent / "networks_seed.json"

# Natural-key column names (in ORM attribute form) used to detect duplicates
# for each table.
_NET_KEY = ("net_name", "client")
_NETLIST_KEY = ("net_num", "line_num")

_DATE_FIELDS = ("date_changed", "start_date", "end_date")


def load_seed_data(json_path: Path = _DEFAULT_SEED_FILE) -> dict:
    with open(json_path, encoding="utf-8") as file:
        content = file.read()

    if not content.strip():
        raise ValueError(f"{json_path} is empty")

    return json.loads(content)


def _parse_dates(record: dict) -> dict:
    record = record.copy()
    for field in _DATE_FIELDS:
        value = record.get(field)
        if isinstance(value, str):
            record[field] = date.fromisoformat(value)
    return record


async def _existing_keys(session, model, key_fields: tuple[str, ...]) -> set[tuple]:
    columns = [getattr(model, field) for field in key_fields]
    rows = (await session.execute(select(*columns))).all()
    return {tuple(row) for row in rows}


async def _seed_table(
    session,
    label: str,
    model,
    records: list[dict],
    key_fields: tuple[str, ...],
) -> None:
    print(f"Seeding {label}...")

    existing_keys = await _existing_keys(session, model, key_fields)

    inserted = 0
    skipped_duplicate = 0
    skipped_malformed = 0
    skipped_db_error = 0

    for raw_record in records:
        try:
            key = tuple(raw_record[field] for field in key_fields)
        except KeyError as e:
            print(f"Skipping malformed {label} record, missing {e}: {raw_record}")
            skipped_malformed += 1
            continue

        if key in existing_keys:
            skipped_duplicate += 1
            continue

        record = _parse_dates(raw_record)

        try:
            async with session.begin_nested():
                session.add(model(**record))
            existing_keys.add(key)
            inserted += 1
        except Exception as e:
            print(f"Failed to insert {label} record {key}: {e}")
            skipped_db_error += 1
            continue

    print(
        f"{inserted} new {label} record(s) inserted. "
        f"Skipped {skipped_duplicate} duplicate(s), "
        f"{skipped_malformed} malformed record(s), "
        f"{skipped_db_error} DB-rejected record(s)."
    )


async def seed_networks() -> None:
    """
    Seed NET and NETLIST.

    Safe to run multiple times. Only records that don't already exist
    (matched by their natural key) are inserted; existing records are
    left untouched.
    """
    data = load_seed_data()

    async with AsyncSessionLocal() as session:
        await _seed_table(session, "net", NetModel, data.get("net", []), _NET_KEY)
        await session.flush()

        await _seed_table(
            session, "netlist", NetListModel, data.get("netlist", []), _NETLIST_KEY
        )
        await session.flush()

        await session.commit()
        print("Networks seeded successfully")


if __name__ == "__main__":
    asyncio.run(seed_networks())
