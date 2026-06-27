import time
import os
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel
import httpx
from bs4 import BeautifulSoup
import structlog
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

logger = structlog.get_logger()

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
# MemoryStore
# ==============================================================================
from services.memory_service import MemoryService
from models.database import async_session
import asyncio

class MemoryStore:
    """Wrapper that delegates to the database-backed MemoryService."""
    def __init__(self):
        pass

    async def _get_service(self):
        # We create a brief local session and service to perform the action
        async with async_session() as session:
            service = MemoryService(session)
            yield service
            
    def _run_async(self, coro):
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(coro)
        except RuntimeError:
            asyncio.run(coro)

    def mark_event_processed(self, event_hash: str, prospect_id: str) -> None:
        async def _run():
            async with async_session() as session:
                service = MemoryService(session)
                await service.mark_event_processed(event_hash, prospect_id)
        self._run_async(_run())
        
    def save_prospect_state(self, prospect_id: str, context: Any) -> None:
        async def _run():
            async with async_session() as session:
                service = MemoryService(session)
                await service.save_prospect_state(context)
        self._run_async(_run())
        
    def rollback_prospect_state(self, prospect_id: str) -> None:
        async def _run():
            async with async_session() as session:
                service = MemoryService(session)
                await service.rollback_prospect_state(prospect_id)
        self._run_async(_run())

# ==============================================================================
# Toolbox
# ==============================================================================
class Toolbox:
    """Facade for external tool interactions."""
    def __init__(self):
        self.circuit_breaker = CircuitBreaker()
        self.event_store = [] # In-memory event store for MVP
        self._llm = None
        
    @property
    def llm(self):
        if not self._llm:
            api_key = os.getenv("OPENAI_API_KEY", "")
            if not api_key:
                logger.warning("OPENAI_API_KEY not found in environment, LLM calls will fail.")
            self._llm = ChatOpenAI(model="gpt-4o", temperature=0.0)
        return self._llm
        
    async def fetch_webpage(self, url: str, timeout_sec: int = 10) -> WebPage:
        start_time = time.time()
        try:
            async with httpx.AsyncClient(timeout=timeout_sec) as client:
                response = await client.get(url)
                response.raise_for_status()
                fetch_time = int((time.time() - start_time) * 1000)
                return WebPage(
                    url=url, 
                    htmlContent=response.text, 
                    statusCode=response.status_code, 
                    fetchTimeMs=fetch_time
                )
        except httpx.TimeoutException:
            raise TimeoutError(f"Timeout fetching {url}")
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                raise RateLimitError(f"Rate limited fetching {url}")
            raise ServiceUnavailableError(f"HTTP error {e.response.status_code} for {url}")
        except Exception as e:
            raise ServiceUnavailableError(f"Failed to fetch {url}: {e}")
            
    async def fetch_crunchbase(self, company_name: str) -> CompanyProfile:
        # Mock logic, as Crunchbase API requires paid access
        # In a real scenario, this would use httpx to call Crunchbase
        return CompanyProfile(name=company_name, employeeCount=150, revenue="10M", industries=["Software"])
        
    async def scrape_linkedin(self, company_name: str) -> dict:
        # Mock logic for LinkedIn scraping
        return {"location": "San Francisco, CA"}
        
    def detect_tech_stack(self, html_content: str, domain: str) -> list[TechStackEntry]:
        # Mock API logic
        soup = BeautifulSoup(html_content, "html.parser")
        text = soup.get_text().lower()
        scripts = " ".join([script.get("src", "").lower() for script in soup.find_all("script")])
        
        stack = []
        if "react" in scripts or "react" in text:
            stack.append(TechStackEntry(technology="React", category="Frontend", confidence=0.8, source="HTML"))
        if "django" in text:
            stack.append(TechStackEntry(technology="Django", category="Backend", confidence=0.7, source="HTML"))
        if "aws" in text or "amazonaws" in text:
            stack.append(TechStackEntry(technology="AWS", category="Cloud", confidence=0.9, source="HTML"))
            
        return stack
        
    def scrape_careers_page(self, url: str) -> list[JobPosting]:
        # Mock logic
        return [JobPosting(title="Engineer", department="Engineering", url=url, postedDate="2026-06-27")]
        
    def validate_email(self, email: str) -> EmailValidationResult:
        # Mock logic
        return EmailValidationResult(email=email, isValid=True, reason="Valid syntax")
        
    def get_competitor_info(self, tech_tag: str) -> Optional[CompetitorMapping]:
        # Mock local mapping
        if tech_tag.lower() == "react":
            return CompetitorMapping(technology=tech_tag, competitors=["Vue", "Angular"], painPoints={"Vue": "Learning curve"})
        if tech_tag.lower() == "aws":
             return CompetitorMapping(technology=tech_tag, competitors=["Azure", "GCP"], painPoints={"Azure": "Complexity"})
        return None
        
    def emit_event(self, event_type: str, payload: Any) -> None:
        logger.info("Emitting event", event_type=event_type, payload=payload)
        self.event_store.append({"type": event_type, "payload": payload, "time": time.time()})

    def send_webhook(self, url: str, payload: Any) -> None:
        # Fire and forget mock
        logger.info("Sending webhook", url=url)
        
    async def generate_text(self, prompt: str, fallback: str) -> str:
        try:
            messages = [SystemMessage(content="You are a prospect summarizer AI."), HumanMessage(content=prompt)]
            response = await self.llm.ainvoke(messages)
            return response.content
        except Exception as e:
            logger.error("LLM generation failed", error=str(e))
            return fallback

    # Phase-2 New Methods
    async def find_company_employees(self, company_name: str) -> list[dict]:
        """Mock method for finding employees via Crunchbase/LinkedIn."""
        logger.info("Finding employees for company", company_name=company_name)
        # In reality this uses HTTPX. Returning mock data matching typical titles.
        return [
            {"name": "Alice Smith", "title": "VP of Engineering", "linkedin_url": "http://linkedin.com/in/alicesmith"},
            {"name": "Bob Jones", "title": "Software Engineer", "linkedin_url": "http://linkedin.com/in/bobjones"},
            {"name": "Carol White", "title": "CTO", "linkedin_url": "http://linkedin.com/in/carolwhite"}
        ]

    async def enrich_contact(self, person_name: str, domain: str) -> dict:
        """Mock method for finding contact info via Hunter.io/Clearbit."""
        logger.info("Enriching contact", person_name=person_name, domain=domain)
        first_name = person_name.split()[0].lower()
        return {
            "email": f"{first_name}@{domain}",
            "phone": "+1-555-0100",
            "linkedin": f"http://linkedin.com/in/{first_name}",
            "confidence_score": 0.85
        }

    async def fetch_rss_entries(self, url: str) -> list[dict]:
        """Mock method for RSS feeds."""
        logger.info("Fetching RSS feed", url=url)
        return [
            {"title": "Acme Corp raises $50M", "summary": "Acme Corp announced series B...", "link": "http://news/1"}
        ]

    async def fetch_news_api(self, keywords: str) -> list[dict]:
        """Mock method for NewsAPI."""
        logger.info("Fetching News API", keywords=keywords)
        return [
            {"title": "Tech startup GlobalScale launches new product", "summary": "GlobalScale is hiring...", "link": "http://news/2"}
        ]

    async def fetch_jobs(self, company: str) -> list[dict]:
        """Mock method for Job board scraping."""
        logger.info("Fetching Jobs", company=company)
        return [{"title": "Senior Engineer", "department": "Engineering"}]

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
