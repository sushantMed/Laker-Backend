"""
Seed script — loads users.json into the database on first run.
Called automatically from app/main.py lifespan, or run standalone:

    python -m app.scripts.seed_users
"""

import json
import sys
from pathlib import Path

from sqlalchemy import select

from app.core.rbac import PERNAME_RESOURCES, SAVE, VIEW
from app.core.security import hash_password
from app.database.session import AsyncSessionLocal
from app.models.permission_model import UserPermissionModel
from app.models.user_model import UserModel

# For mocking in the db

sys.path.append(str(Path(__file__).resolve().parents[1]))


def load_users(json_file):
    with open(json_file, encoding="utf-8") as file:
        content = file.read()

    print("JSON FILE:", json_file)
    print("CONTENT:", repr(content))
    if not content.strip():
        raise ValueError(f"{json_file} is empty")

    return json.loads(content)


def _grants_for(spec) -> list[UserPermissionModel]:
    """Turn a users.json ``permissions`` block into user_permissions rows.

    ``"*"`` means every known screen with both actions; otherwise it is the same
    ``{pername: [actions]}`` shape /auth/me returns.
    """
    if spec == "*":
        spec = {p: [VIEW, SAVE] for p in PERNAME_RESOURCES}

    return [
        UserPermissionModel(
            pername=pername,
            viewperm="Y" if VIEW in flags else "N",
            saveperm="Y" if SAVE in flags else "N",
        )
        for pername, flags in spec.items()
    ]


async def seed_users():
    json_path = Path(__file__).parent / "users.json"

    users = load_users(json_path)

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(UserModel))
        existing_user = result.first()

        if existing_user:
            print("Users already exist. Skipping seed.")

        for user_data in users:
            email = user_data["email"].lower()

            result = await session.execute(
                select(UserModel).where(UserModel.email == email)
            )

            existing_user = result.scalar_one_or_none()

            if existing_user:
                print(f"User already exists: {email}")
                continue

            user = UserModel(
                email=email,
                first_name=user_data["first_name"],
                last_name=user_data["last_name"],
                hashed_password=hash_password(user_data["password"]),
                status="ACTIVE",
                grants=_grants_for(user_data.get("permissions", {})),
            )

            session.add(user)

            print(f"Added user: {email}")

        await session.commit()

    print("\nUsers seeded successfully.")


if __name__ == "__main__":
    import asyncio

    asyncio.run(seed_users())
