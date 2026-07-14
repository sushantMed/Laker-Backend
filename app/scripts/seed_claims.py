"""
Seed the claims table from a JSON file.
This script is intended to be run as a standalone program, not imported as a module.

Usage:
    python app/scripts/seed_claims.py [--file PATH] [--skip-missing-members]

Options:
    --file PATH: Path to the claims JSON file (default: app/seed_data/claims.json).
    --skip-missing-members: Skip (instead of aborting on) claims whose memberId doesn't exist.

Behavior:
- Safe to run multiple times. Claims already present in the DB (matched by authNum)
  are skipped; only genuinely new claims are inserted.
- Each claim is inserted in its own SAVEPOINT, so a single bad/rejected record
  (e.g. a DB constraint violation) does not roll back the other valid claims
  in the same run.

Assumptions:
- The database is already set up and accessible via the AsyncSessionLocal factory.
- The members table is already populated with the memberIds referenced in the claims JSON.
- The claims JSON file is structured as a list of claim records, each with camelCase keys
  matching the ClaimModel fields (e.g., claimId, authNum, memberId, rxNumber, drug, ndc,
  dateFilled, dateWritten, quantity, daysSupply, refillsRemaining, pharmacyNpi,
  pharmacyName, prescriberNpi, prescriberName, ingredientCost, dispensingFee, copay,
  totalPaid, isTestClaim, planId).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import uuid
from datetime import date, datetime
from pathlib import Path

from sqlalchemy import select

import app.models  # noqa: F401 (registers every ORM mapper for relationship resolution)
from app.database.session import AsyncSessionLocal
from app.models.claim_model import ClaimModel
from app.models.member_model import MemberModel

_DEFAULT_SEED_FILE = Path(__file__).resolve().parent.parent / "scripts" / "claims.json"


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    return datetime.strptime(value, "%Y-%m-%d").date()


def _claim_from_record(record: dict) -> ClaimModel:
    """Map a single JSON record (camelCase) onto a ClaimModel instance."""
    return ClaimModel(
        claim_id=record.get("claimId") or str(uuid.uuid4()),
        auth_num=record["authNum"],
        member_id=record["memberId"],
        rx_number=record["rxNumber"],
        drug_name=record["drug"],
        ndc=record["ndc"],
        date_filled=_parse_date(record["dateFilled"]),
        date_written=_parse_date(record.get("dateWritten")),
        quantity=record.get("quantity"),
        days_supply=record.get("daysSupply"),
        refills_remaining=record.get("refillsRemaining"),
        pharmacy_npi=record.get("pharmacyNpi"),
        pharmacy_name=record.get("pharmacyName"),
        prescriber_npi=record.get("prescriberNpi"),
        prescriber_name=record.get("prescriberName"),
        ingredient_cost=record.get("ingredientCost"),
        dispensing_fee=record.get("dispensingFee"),
        copay=record.get("copay"),
        total_paid=record.get("totalPaid"),
        is_test_claim=record.get("isTestClaim", False),
        plan_id=record.get("planId"),
    )


async def seed_claims(file_path: Path, skip_missing_members: bool) -> None:
    if not file_path.exists():
        print(f"Seed file not found: {file_path}")
        return

    records = json.loads(file_path.read_text())
    if not records:
        print(f"No records found in {file_path}.")
        return

    async with AsyncSessionLocal() as session:
        # Claims already in the DB — this is the ONLY thing that causes a skip
        # for duplicates. Everything else (missing member, bad DB insert) is
        # tracked separately so it's clear why a record was left out.
        existing_auth_nums = set(
            (await session.execute(select(ClaimModel.auth_num))).scalars().all()
        )
        known_member_ids = set(
            (await session.execute(select(MemberModel.member_id))).scalars().all()
        )

        inserted = 0
        skipped_duplicate = 0
        skipped_missing_member = 0
        skipped_malformed = 0
        skipped_db_error = 0

        for record in records:
            try:
                auth_num = record["authNum"]
                member_id = record["memberId"]
            except KeyError as e:
                print(f"Skipping malformed record, missing key {e}: {record}")
                skipped_malformed += 1
                continue

            # Skip only claims that already exist in the DB (by auth_num)
            if auth_num in existing_auth_nums:
                skipped_duplicate += 1
                continue

            if member_id not in known_member_ids:
                if skip_missing_members:
                    skipped_missing_member += 1
                    continue
                print(
                    f"Member '{member_id}' (referenced by claim '{auth_num}') "
                    "does not exist. Seed members first, or re-run with "
                    "--skip-missing-members to skip just these records."
                )
                return

            try:
                claim = _claim_from_record(record)
            except KeyError as e:
                print(f"Skipping malformed record, missing key {e}: {record}")
                skipped_malformed += 1
                continue

            # Per-record SAVEPOINT: if this insert fails (constraint violation,
            # bad value, etc.), only this claim is rolled back — everything
            # already added in this run is unaffected.
            try:
                async with session.begin_nested():
                    session.add(claim)
                existing_auth_nums.add(auth_num)
                inserted += 1
            except Exception as e:
                print(f"Failed to insert claim '{auth_num}': {e}")
                skipped_db_error += 1
                continue

        if inserted:
            await session.commit()

        print(f"Seeded {inserted} claim(s) successfully.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed the claims table from JSON.")
    parser.add_argument(
        "--file",
        type=Path,
        default=_DEFAULT_SEED_FILE,
        help=f"Path to the claims JSON file (default: {_DEFAULT_SEED_FILE}).",
    )
    parser.add_argument(
        "--skip-missing-members",
        action="store_true",
        help="Skip (instead of aborting on) claims whose memberId doesn't exist.",
    )
    args = parser.parse_args()

    asyncio.run(
        seed_claims(file_path=args.file, skip_missing_members=args.skip_missing_members)
    )


if __name__ == "__main__":
    main()
