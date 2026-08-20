"""
Seed the legacy SUBSCRIBER / cardholder-eligibility lookup tables
(SUBSCRIBER, GROUPS, SUBSCRIBERGROUPLIST, SUBSCOB, SUBSSUBGROUPS,
SUBSCRIBERELIGLIST) from a JSON file. Safe to run on application startup,
and safe to run multiple times.

Behavior:
- Only records that don't already exist in the DB (matched by their natural
  key -- see the _*_KEY tuples below) are inserted. Records that already
  exist are skipped, not re-inserted or updated.
- Each record is inserted in its own SAVEPOINT, so a single bad/rejected
  record (e.g. a DB constraint violation) does not roll back the other
  valid records in the same run.

NOTE: subscribernum / subscriber values in the seed file reuse cardholder
member_id values already seeded by seed_members.py (see members.json),
so a cardholder's eligibility chain resolves end-to-end. Run
seed_members.py first if seeding a fresh database.
"""

from __future__ import annotations

import asyncio
import json
from datetime import date
from pathlib import Path

from sqlalchemy import select

from app.database.session import AsyncSessionLocal
from app.models.groups_model import GroupsModel
from app.models.member_model import Subscriber
from app.models.subs_subgroups_model import SubsSubgroupsModel
from app.models.subscob_model import SubscobModel
from app.models.subscriber_elig_list_model import SubscriberEligListModel
from app.models.subscriber_group_list_model import SubscriberGroupListModel

_DEFAULT_SEED_FILE = Path(__file__).resolve().parent / "eligibility_seed.json"

# Natural-key column names (in ORM attribute form) used to detect duplicates
# for each table. Change these if your actual models use different field
# names.
_SUBSCRIBER_KEY = ("subscribernum", "personcode", "clientcode")
_GROUPS_KEY = ("groupnum",)
_SUBSCRIBER_GROUP_LIST_KEY = ("subscriber", "clientcode", "linenum")
_SUBSCOB_KEY = ("subscriber", "pc", "linenum")
_SUBS_SUBGROUPS_KEY = ("subscriber", "pc", "linenum", "subgroup")
_SUBSCRIBER_ELIG_LIST_KEY = ("subscriber", "personcode", "clientcode", "linenum")

_DATE_FIELDS = ("startdt", "enddt", "changedt", "lastchanged", "dob", "termination")


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


async def seed_eligibility() -> None:
    """
    Seed SUBSCRIBER, GROUPS, SUBSCRIBERGROUPLIST, SUBSCOB, SUBSSUBGROUPS
    and SUBSCRIBERELIGLIST.

    Safe to run multiple times. Only records that don't already exist
    (matched by their natural key) are inserted; existing records are
    left untouched.
    """
    data = load_seed_data()

    async with AsyncSessionLocal() as session:
        await _seed_table(
            session,
            "subscriber",
            Subscriber,
            data.get("subscribers", []),
            _SUBSCRIBER_KEY,
        )
        await session.flush()

        await _seed_table(
            session, "group", GroupsModel, data.get("groups", []), _GROUPS_KEY
        )
        await session.flush()

        await _seed_table(
            session,
            "subscriber-group-list",
            SubscriberGroupListModel,
            data.get("subscriberGroupList", []),
            _SUBSCRIBER_GROUP_LIST_KEY,
        )
        await session.flush()

        await _seed_table(
            session, "subscob", SubscobModel, data.get("subscob", []), _SUBSCOB_KEY
        )
        await session.flush()

        await _seed_table(
            session,
            "sub-subgroup",
            SubsSubgroupsModel,
            data.get("subsSubgroups", []),
            _SUBS_SUBGROUPS_KEY,
        )
        await session.flush()

        await _seed_table(
            session,
            "subscriber-elig-list",
            SubscriberEligListModel,
            data.get("subscriberEligList", []),
            _SUBSCRIBER_ELIG_LIST_KEY,
        )
        await session.flush()

        await session.commit()
        print("Eligibility lookups seeded successfully")


if __name__ == "__main__":
    asyncio.run(seed_eligibility())
