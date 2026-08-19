"""
Seed script — loads users.json into the database, syncing existing users'
grants to whatever the JSON (and PERNAME_RESOURCES) currently say.

Not called automatically anywhere (app/main.py's lifespan does not invoke
it, despite what an earlier version of this docstring claimed) -- run it
manually after editing users.json:

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


def _sync_grants(user: UserModel, desired: list[UserPermissionModel]) -> None:
    """Add missing grants and update changed ones for an existing user.

    Never removes a grant that's absent from ``desired`` -- other seed paths
    (e.g. alembic data migrations) may have granted screens this user's JSON
    entry doesn't list, and a sync run shouldn't silently revoke those.
    """
    existing = {g.pername.strip().lower(): g for g in user.grants}
    for grant in desired:
        current = existing.get(grant.pername.strip().lower())
        if current is None:
            user.grants.append(grant)
        elif current.viewperm != grant.viewperm or current.saveperm != grant.saveperm:
            current.viewperm = grant.viewperm
            current.saveperm = grant.saveperm


async def seed_users():
    json_path = Path(__file__).parent / "users.json"

    users = load_users(json_path)

    async with AsyncSessionLocal() as session:
        for user_data in users:
            email = user_data["email"].lower()

            result = await session.execute(
                select(UserModel).where(UserModel.email == email)
            )
            existing_user = result.scalar_one_or_none()
            desired_grants = _grants_for(user_data.get("permissions", {}))

            if existing_user is None:
                user = UserModel(
                    email=email,
                    first_name=user_data["first_name"],
                    last_name=user_data["last_name"],
                    hashed_password=hash_password(user_data["password"]),
                    status="ACTIVE",
                    grants=desired_grants,
                )
                session.add(user)
                print(f"Added user: {email}")
                continue

            # Sync name + grants on every run. Password is intentionally left
            # alone here so a restart never silently resets someone's password
            # back to the JSON default.
            existing_user.first_name = user_data["first_name"]
            existing_user.last_name = user_data["last_name"]
            _sync_grants(existing_user, desired_grants)
            print(f"Synced user: {email}")

        await session.commit()

    print("\nUsers seeded successfully.")


if __name__ == "__main__":
    import asyncio

    asyncio.run(seed_users())
