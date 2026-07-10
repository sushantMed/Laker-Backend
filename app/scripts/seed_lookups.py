import json
from pathlib import Path

from sqlalchemy import select

from app.database.session import AsyncSessionLocal
from app.models.drug_model import DrugModel
from app.models.pharmacy_model import PharmacyModel
from app.models.prescriber_model import PrescriberModel
from app.utils.enums import BrandGeneric, Maintenance


def load_seed_data():
    json_path = Path(__file__).parent / "lookups_seed.json"

    with open(json_path, encoding="utf-8") as file:
        content = file.read()

    if not content.strip():
        raise ValueError(f"{json_path} is empty")

    return json.loads(content)


async def seed_lookups():
    data = load_seed_data()

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(DrugModel))
        if result.first():
            print("Lookups already exist. Skipping seed.")
            return

        print("Seeding drugs...")
        for drug_data in data.get("drugs", []):
            drug_data = drug_data.copy()
            drug_data["brand_generic"] = BrandGeneric(drug_data["brand_generic"])
            drug_data["maintenance"] = Maintenance(drug_data["maintenance"])
            session.add(DrugModel(**drug_data))
        await session.flush()
        print(f"✓ {len(data.get('drugs', []))} drugs inserted")

        print("Seeding pharmacies...")
        for pharmacy_data in data.get("pharmacies", []):
            session.add(PharmacyModel(**pharmacy_data))
        await session.flush()
        print(f"✓ {len(data.get('pharmacies', []))} pharmacies inserted")

        print("Seeding prescribers...")
        for prescriber_data in data.get("prescribers", []):
            session.add(PrescriberModel(**prescriber_data))
        await session.flush()
        print(f"✓ {len(data.get('prescribers', []))} prescribers inserted")

        await session.commit()
        print("✓ Lookups seeded successfully")


if __name__ == "__main__":
    import asyncio

    asyncio.run(seed_lookups())
