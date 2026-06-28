from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Dict, Any

from services.scraping_service import ScrapingService
from services.enrichment_service import EnrichmentService

router = APIRouter(prefix="/api/sandbox", tags=["sandbox"])

def get_scraping_service() -> ScrapingService:
    return ScrapingService()

def get_enrichment_service() -> EnrichmentService:
    return EnrichmentService()

class ScrapeRequest(BaseModel):
    url: str

class EnrichRequest(BaseModel):
    company: str

@router.post("/scrape", response_model=Dict[str, Any])
async def sandbox_scrape(
    req: ScrapeRequest,
    scraping_service: ScrapingService = Depends(get_scraping_service)
):
    try:
        return await scraping_service.sandbox_scrape(req.url)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/enrich", response_model=Dict[str, Any])
async def sandbox_enrich(
    req: EnrichRequest,
    enrichment_service: EnrichmentService = Depends(get_enrichment_service)
):
    try:
        return await enrichment_service.sandbox_enrich(req.company)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
