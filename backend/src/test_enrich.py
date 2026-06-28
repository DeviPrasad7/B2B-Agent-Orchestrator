import asyncio
from services.enrichment_service import EnrichmentService

async def test_enrich():
    service = EnrichmentService()
    print("Testing fetch_crunchbase...")
    try:
        profile = await service.fetch_crunchbase("ChatGPT")
        print("Crunchbase Profile:", profile)
        
        print("Testing find_company_employees...")
        emps = await service.find_company_employees("ChatGPT")
        print("Employees:", emps)
    except Exception as e:
        print("Error:", str(e))

if __name__ == "__main__":
    asyncio.run(test_enrich())
