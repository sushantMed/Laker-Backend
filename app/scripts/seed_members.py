"""
Seed script for plans, members and addresses.
Safe to run on application startup.
"""

import json
from datetime import date
from pathlib import Path

from sqlalchemy import select

from app.database.session import AsyncSessionLocal
from app.models.member_address_model import MemberAddressModel
from app.models.member_model import MemberModel
from app.models.plan_model import PlanModel
from app.utils.enums import CoverageType, Gender


def load_seed_data():
    json_path = Path(__file__).parent / "members.json"

    with open(json_path, encoding="utf-8") as file:
        content = file.read()

    if not content.strip():
        raise ValueError(f"{json_path} is empty")

    return json.loads(content)


async def seed_members():
    data = load_seed_data()

    async with AsyncSessionLocal() as session:
        # --------------------------------------------------
        # Plans (upsert by plan_id)
        # --------------------------------------------------
        existing_plan_ids = set(
            (await session.execute(select(PlanModel.plan_id))).scalars().all()
        )
        new_plans = [
            p for p in data.get("plans", []) if p["plan_id"] not in existing_plan_ids
        ]
        for plan_data in new_plans:
            session.add(PlanModel(**plan_data))
        await session.flush()
        print(f"{len(new_plans)} new plans inserted")

        # --------------------------------------------------
        # Members (upsert by member_id)
        # --------------------------------------------------
        existing_member_ids = set(
            (await session.execute(select(MemberModel.member_id))).scalars().all()
        )

        cardholders, dependents = [], []

        for member_data in data.get("members", []):
            if member_data["member_id"] in existing_member_ids:
                continue  # already seeded, skip

            member_data = member_data.copy()
            member_data["date_of_birth"] = date.fromisoformat(
                member_data["date_of_birth"]
            )
            member_data["start_date"] = date.fromisoformat(member_data["start_date"])
            member_data["end_date"] = date.fromisoformat(member_data["end_date"])

            if member_data.get("gender"):
                member_data["gender"] = Gender(member_data["gender"])
            if member_data.get("cov_type"):
                member_data["cov_type"] = CoverageType(member_data["cov_type"])

            member = MemberModel(**member_data)
            (dependents if member.subscriber_member_id else cardholders).append(member)

        session.add_all(cardholders)
        await session.flush()
        session.add_all(dependents)
        await session.flush()
        print(f"{len(cardholders)} new cardholders inserted")
        print(f"{len(dependents)} new dependents inserted")

        # --------------------------------------------------
        # Addresses (upsert by member_id)
        # --------------------------------------------------
        existing_addr_member_ids = set(
            (await session.execute(select(MemberAddressModel.member_id)))
            .scalars()
            .all()
        )
        new_addresses = [
            a
            for a in data.get("addresses", [])
            if a["member_id"] not in existing_addr_member_ids
        ]
        for address_data in new_addresses:
            session.add(MemberAddressModel(**address_data))
        await session.flush()
        print(f"{len(new_addresses)} new addresses inserted")

        await session.commit()
        print("Seed completed successfully")


if __name__ == "__main__":
    import asyncio

    asyncio.run(seed_members())
