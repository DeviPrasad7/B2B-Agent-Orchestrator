"""
Toolbox – Facade for external tool interactions.

This module retains only the ``Toolbox`` class. The other utilities that
previously lived here have been extracted to focused modules:
  - core.circuit_breaker  – CircuitBreaker, CircuitBreakerState
  - core.exceptions       – RateLimitError, TimeoutError, ServiceUnavailableError
  - models.dto            – WebPage, CompanyProfile, TechStackEntry, etc.

Re-exports are provided below for backward compatibility so existing imports
such as ``from agent.utils import CircuitBreaker`` continue to work during
the migration period.
"""

import time
from enum import Enum
from typing import Any, Optional

import structlog

# ---------------------------------------------------------------------------
# Re-exports from focused modules (backward compat)
# ---------------------------------------------------------------------------
from core.circuit_breaker import CircuitBreaker, CircuitBreakerState  # noqa: F401
from core.exceptions import (  # noqa: F401
    RateLimitError,
    ServiceUnavailableError,
)
# TimeoutError shadows built-in – import explicitly if needed
from core.exceptions import TimeoutError as AgentTimeoutError  # noqa: F401
from models.dto import (  # noqa: F401
    WebPage,
    CompanyProfile,
    TechStackEntry,
    JobPosting,
    EmailValidationResult,
    CompetitorMapping,
)
from services.interfaces import (  # noqa: F401
    LLMServiceProtocol,
    ScrapingServiceProtocol,
    EnrichmentServiceProtocol,
)
from core.logging import logger


# ---------------------------------------------------------------------------
# Domain enums (kept here as they are agent-layer concerns)
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# Toolbox (Facade)
# ---------------------------------------------------------------------------
class Toolbox:
    """Facade for external tool interactions. Aggregates internal services.

    Accepts service instances typed against Protocol interfaces so that
    concrete implementations can be swapped freely (Dependency Inversion).
    """

    def __init__(
        self,
        llm_service: LLMServiceProtocol,
        scraping_service: ScrapingServiceProtocol,
        enrichment_service: EnrichmentServiceProtocol,
    ):
        # NOTE: In a multi-worker cluster, replace CircuitBreaker with a
        # Redis-backed implementation so all workers share failure counts.
        self.circuit_breaker = CircuitBreaker()
        self.event_store: list[dict] = []  # In-memory; replace with Redis in prod

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
        # Fire and forget mock – integrate a real HTTP client in production
        logger.info("Sending webhook", url=url)

    async def generate_text(self, prompt: str, fallback: str, require_json: bool = False, strategy: str = "heavy") -> str:
        return await self._llm_service.generate_text(prompt, fallback, require_json=require_json, strategy=strategy)

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


# ---------------------------------------------------------------------------
# MonitoringService – kept as a thin structlog wrapper for backward compat.
# Deprecation notice: use structlog.get_logger() directly in new code.
# ---------------------------------------------------------------------------
class MonitoringService:
    @staticmethod
    def log_success(prospect_id: str, message: str = "") -> None:
        logger.info("SUCCESS", prospect_id=prospect_id, detail=message)

    @staticmethod
    def log_error(prospect_id: str, error_code: str) -> None:
        logger.error("ERROR", prospect_id=prospect_id, error_code=error_code)

    @staticmethod
    def log_warning(prospect_id: str, message: str) -> None:
        logger.warning("WARNING", prospect_id=prospect_id, detail=message)

    @staticmethod
    def log_info(prospect_id: str, message: str) -> None:
        logger.info("INFO", prospect_id=prospect_id, detail=message)
