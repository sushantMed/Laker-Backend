"""
Seed the claims table from a JSON file.
This script is intended to be run as a standalone program, not imported as a module.
Usage:
    python app/scripts/seed_claims.py [--file PATH] [--skip-missing-members]
Options:
    --file PATH: Path to the claims JSON file (default: app/seed_data/claims.json).
    --skip-missing-members: Skip (instead of aborting on) claims whose memberId doesn't exist.
Assumptions:
- The database is already set up and accessible via the AsyncSessionLocal factory.
- The members table is already populated with the memberIds referenced in the claims JSON.
- The claims JSON file is structured as a list of claim records, each with camelCase keys
  matching the ClaimModel fields (e.g., claimId, authNum, memberId,
"""
from __future__ import annotations

import argparse
import asyncio
import json
import uuid
from datetime import date, datetime
from pathlib import Path

from sqlalchemy import select
from app.database.session import AsyncSessionLocal

from app.models.claim_model import ClaimModel
from app.models.member_model import MemberModel
from app.models.plan_model import PlanModel
from app.models.member_address_model import MemberAddressModel



_DEFAULT_SEED_FILE = Path(__file__).resolve().parent.parent   / "scripts" / "claims.json"

print(_DEFAULT_SEED_FILE)

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
        # pharmacy_nabp=record.get("pharmacyNabp"),
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
        existing_auth_nums = set(
            (await session.execute(select(ClaimModel.auth_num))).scalars().all()
        )
        known_member_ids = set(
            (await session.execute(select(MemberModel.member_id))).scalars().all()
        )

        new_claims: list[ClaimModel] = []
        skipped_duplicate = 0
        skipped_missing_member = 0

        for record in records:
            auth_num = record["authNum"]
            member_id = record["memberId"]

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

            new_claims.append(_claim_from_record(record))
            existing_auth_nums.add(auth_num)

        if not new_claims:
            print(
                f"Nothing to insert. Skipped {skipped_duplicate} duplicate(s), "
                f"{skipped_missing_member} missing-member record(s)."
            )
            return

        session.add_all(new_claims)
        await session.commit()
        print(
            f"Seeded {len(new_claims)} claim(s) from {file_path}. "
            f"Skipped {skipped_duplicate} duplicate(s), "
            f"{skipped_missing_member} missing-member record(s)."
        )


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
