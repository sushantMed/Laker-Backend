class PharmacyRepository:
    def __init__(self, session):
        self.session = session

    async def get_pharmacy_by_npi(self, npi: str):
        # Implement the logic to retrieve a pharmacy by NPI from the database
        pass

    async def get_pharmacy_by_nabp(self, nabp: str):
        # Implement the logic to retrieve a pharmacy by NABP from the database
        pass

    