import time
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel
from core.logging import logger

# ==============================================================================
# Custom Exceptions
# ==============================================================================
class RateLimitError(Exception):
    pass

class TimeoutError(Exception):
    pass

class ServiceUnavailableError(Exception):
    pass

# ==============================================================================
# Domain Models (DTOs)
# ==============================================================================
class AgentStatus(Enum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"
    AWAITING_HUMAN = "AWAITING_HUMAN"

class ProspectStatus(Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    NO_ACTION = "NO_ACTION"
    FORCE_HITL = "FORCE_HITL"
    COMPLETED = "COMPLETED"
    REJECTED = "REJECTED"
    TIMEOUT = "TIMEOUT"

class WebPage(BaseModel):
    url: str
    htmlContent: str
    statusCode: int
    fetchTimeMs: int

class CompanyProfile(BaseModel):
    name: str
    description: Optional[str] = None
    employeeCount: Optional[int] = None
    revenue: Optional[str] = None
    location: Optional[str] = None
    industries: list[str] = []

class TechStackEntry(BaseModel):
    technology: str
    category: str
    confidence: float
    source: str

class JobPosting(BaseModel):
    title: str
    department: str
    url: str
    postedDate: str

class EmailValidationResult(BaseModel):
    email: str
    isValid: bool
    reason: str

class CompetitorMapping(BaseModel):
    technology: str
    competitors: list[str]
    painPoints: dict[str, str]

# ==============================================================================
# CircuitBreaker
# ==============================================================================
class CircuitBreakerState(Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"

class CircuitBreaker:
    """Emulates a circuit breaker for external dependencies."""
    def __init__(self, failure_threshold: int = 3, reset_timeout_sec: int = 30):
        self.service_states: dict[str, CircuitBreakerState] = {}
        self.failure_counts: dict[str, int] = {}
        self.last_failure_times: dict[str, float] = {}
        self.failure_threshold = failure_threshold
        self.reset_timeout_sec = reset_timeout_sec
        
    def check_health(self, service_name: str) -> CircuitBreakerState:
        state = self.service_states.get(service_name, CircuitBreakerState.CLOSED)
        if state == CircuitBreakerState.OPEN:
            last_time = self.last_failure_times.get(service_name, 0)
            if time.time() - last_time > self.reset_timeout_sec:
                self.service_states[service_name] = CircuitBreakerState.HALF_OPEN
                return CircuitBreakerState.HALF_OPEN
            return CircuitBreakerState.OPEN
        return state
        
    def record_success(self, service_name: str) -> None:
        self.failure_counts[service_name] = 0
        self.service_states[service_name] = CircuitBreakerState.CLOSED
        
    def record_failure(self, service_name: str) -> None:
        count = self.failure_counts.get(service_name, 0) + 1
        self.failure_counts[service_name] = count
        
        state = self.service_states.get(service_name, CircuitBreakerState.CLOSED)
        
        if state == CircuitBreakerState.HALF_OPEN or count >= self.failure_threshold:
            self.service_states[service_name] = CircuitBreakerState.OPEN

# ==============================================================================
# Toolbox (Facade)
# ==============================================================================
class Toolbox:
    """Facade for external tool interactions. Aggregates internal services."""
    def __init__(self, llm_service=None, scraping_service=None, enrichment_service=None):
        if llm_service is None:
            from services.llm_service import LLMService
            llm_service = LLMService()
        if scraping_service is None:
            from services.scraping_service import ScrapingService
            scraping_service = ScrapingService()
        if enrichment_service is None:
            from services.enrichment_service import EnrichmentService
            enrichment_service = EnrichmentService()

        self.circuit_breaker = CircuitBreaker()
        self.event_store = [] # In-memory event store for MVP
        
        # Sub-services
        self._llm_service = llm_service
        self._scraping_service = scraping_service
        self._enrichment_service = enrichment_service
        
    async def fetch_webpage(self, url: str, timeout_sec: int = 10) -> WebPage:
        return await self._scraping_service.fetch_webpage(url, timeout_sec)
            
    async def fetch_crunchbase(self, company_name: str) -> CompanyProfile:
        return await self._enrichment_service.fetch_crunchbase(company_name)
        
    async def scrape_linkedin(self, company_name: str) -> dict:
        return await self._enrichment_service.scrape_linkedin(company_name)
        
    def detect_tech_stack(self, html_content: str, domain: str) -> list[TechStackEntry]:
        return self._scraping_service.detect_tech_stack(html_content, domain)
        
    def scrape_careers_page(self, url: str) -> list[JobPosting]:
        return self._scraping_service.scrape_careers_page(url)
        
    def validate_email(self, email: str) -> EmailValidationResult:
        return self._enrichment_service.validate_email(email)
        
    def get_competitor_info(self, tech_tag: str) -> Optional[CompetitorMapping]:
        return self._enrichment_service.get_competitor_info(tech_tag)
        
    def emit_event(self, event_type: str, payload: Any) -> None:
        logger.info("Emitting event", event_type=event_type, payload=payload)
        self.event_store.append({"type": event_type, "payload": payload, "time": time.time()})

    def send_webhook(self, url: str, payload: Any) -> None:
        # Fire and forget mock
        logger.info("Sending webhook", url=url)
        
    async def generate_text(self, prompt: str, fallback: str) -> str:
        return await self._llm_service.generate_text(prompt, fallback)

    async def find_company_employees(self, company_name: str) -> list[dict]:
        return await self._enrichment_service.find_company_employees(company_name)

    async def enrich_contact(self, person_name: str, domain: str) -> dict:
        return await self._enrichment_service.enrich_contact(person_name, domain)

    async def fetch_rss_entries(self, url: str) -> list[dict]:
        return await self._enrichment_service.fetch_rss_entries(url)

    async def fetch_news_api(self, keywords: str) -> list[dict]:
        return await self._enrichment_service.fetch_news_api(keywords)

    async def fetch_jobs(self, company: str) -> list[dict]:
        return await self._enrichment_service.fetch_jobs(company)

# ==============================================================================
# Emulated MonitoringService
# ==============================================================================
class MonitoringService:
    @staticmethod
    def log_success(prospect_id: str, message: str = ""):
        logger.info("SUCCESS", prospect_id=prospect_id, message=message)

    @staticmethod
    def log_error(prospect_id: str, error_code: str):
        logger.error("ERROR", prospect_id=prospect_id, error_code=error_code)
        
    @staticmethod
    def log_warning(prospect_id: str, message: str):
        logger.warning("WARNING", prospect_id=prospect_id, message=message)

    @staticmethod
    def log_info(prospect_id: str, message: str):
        logger.info("INFO", prospect_id=prospect_id, message=message)
