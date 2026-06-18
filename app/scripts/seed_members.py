"""
Seed script for plans, members and addresses.
Safe to run on application startup.
"""

import json
from datetime import date
from pathlib import Path

from app.database.session import AsyncSessionLocal
from sqlalchemy import select 
from app.models.plan_model import PlanModel
from app.models.member_model import MemberModel
from app.models.member_address_model import MemberAddressModel
from app.utils.enums import Gender, CoverageType


def load_seed_data():
    json_path = Path(__file__).parent / "members.json"

    with open(json_path, "r", encoding="utf-8") as file:
        content = file.read()

    if not content.strip():
        raise ValueError(f"{json_path} is empty")

    return json.loads(content)


async def seed_members():
    """
    Seed plans, members and addresses.

    Safe to run multiple times.
    If members already exist, seeding is skipped.
    """

    data = load_seed_data()

    async with AsyncSessionLocal() as session:

        # Skip if data already exists
        result = await session.execute(select(MemberModel))

        if result.first():
            print("Members already exist. Skipping seed.")
            return

        # --------------------------------------------------
        # Plans
        # --------------------------------------------------

        print("Seeding plans...")

        for plan_data in data.get("plans", []):
            session.add(
                PlanModel(**plan_data)
            )

        await session.flush()

        print(
            f"✓ {len(data.get('plans', []))} plans inserted"
        )

        # --------------------------------------------------
        # Members
        # --------------------------------------------------

        print("Seeding members...")

        cardholders = []
        dependents = []

        for member_data in data.get("members", []):

            # Avoid mutating original JSON dict
            member_data = member_data.copy()

            # Date conversion
            member_data["date_of_birth"] = date.fromisoformat(
                member_data["date_of_birth"]
            )

            member_data["start_date"] = date.fromisoformat(
                member_data["start_date"]
            )

            member_data["end_date"] = date.fromisoformat(
                member_data["end_date"]
            )

            # Enum conversion
            if member_data.get("gender"):
                member_data["gender"] = Gender(
                    member_data["gender"]
                )

            if member_data.get("cov_type"):
                member_data["cov_type"] = CoverageType(
                    member_data["cov_type"]
                )

            member = MemberModel(**member_data)

            if member.subscriber_member_id:
                dependents.append(member)
            else:
                cardholders.append(member)

        # Insert cardholders first
        session.add_all(cardholders)
        await session.flush()

        # Insert dependents second
        session.add_all(dependents)
        await session.flush()

        print(
            f"✓ {len(cardholders)} cardholders inserted"
        )

        print(
            f"✓ {len(dependents)} dependents inserted"
        )

        # --------------------------------------------------
        # Addresses
        # --------------------------------------------------

        print("Seeding addresses...")

        for address_data in data.get("addresses", []):
            session.add(
                MemberAddressModel(**address_data)
            )

        await session.flush()

        print(
            f"✓ {len(data.get('addresses', []))} addresses inserted"
        )

        # --------------------------------------------------
        # Commit
        # --------------------------------------------------

        await session.commit()

        print("✓ Members seeded successfully")


if __name__ == "__main__":
    import asyncio

    asyncio.run(seed_members())