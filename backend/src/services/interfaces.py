"""
Service Protocol interfaces for the ICP Agent platform.

These `typing.Protocol` types define the contracts that concrete services
must fulfil. Depending on Protocols (rather than concrete classes) allows:
- Swapping service implementations without changing agent code.
- Easy mocking in tests without subclassing.
- Static type-checker validation of service conformance.

Usage in Toolbox:
    def __init__(
        self,
        llm_service: LLMServiceProtocol,
        scraping_service: ScrapingServiceProtocol,
        enrichment_service: EnrichmentServiceProtocol,
    ): ...
"""

from typing import Protocol, Optional, runtime_checkable
from models.dto import WebPage, CompanyProfile, TechStackEntry, JobPosting, EmailValidationResult, CompetitorMapping


@runtime_checkable
class LLMServiceProtocol(Protocol):
    """Contract for any LLM text-generation backend."""

    async def generate_text(
        self, prompt: str, fallback: str, require_json: bool = False, strategy: str = "heavy"
    ) -> str:
        """Generate text from a prompt. Falls back to ``fallback`` on error."""
        ...


@runtime_checkable
class ScrapingServiceProtocol(Protocol):
    """Contract for web-scraping and tech-stack detection services."""

    async def fetch_webpage(self, url: str, timeout_sec: int = 10) -> WebPage:
        """Fetch a URL and return structured page content."""
        ...

    async def detect_tech_stack(self, html_content: str, domain: str) -> list[TechStackEntry]:
        """Detect technologies from HTML content and domain signals."""
        ...

    async def scrape_careers_page(self, url: str) -> list[JobPosting]:
        """Scrape job postings from a careers page."""
        ...


@runtime_checkable
class EnrichmentServiceProtocol(Protocol):
    """Contract for data enrichment services (Crunchbase, LinkedIn, etc.)."""

    async def fetch_crunchbase(self, company_name: str) -> CompanyProfile:
        """Fetch enriched company data from Crunchbase."""
        ...

    async def scrape_linkedin(self, company_name: str) -> dict:
        """Scrape LinkedIn profile data for a company."""
        ...

    def validate_email(self, email: str) -> EmailValidationResult:
        """Validate an email address."""
        ...

    async def get_competitor_info(self, tech_tag: str) -> Optional[CompetitorMapping]:
        """Retrieve competitor mapping for a given technology tag."""
        ...

    async def find_company_employees(self, company_name: str) -> list[dict]:
        """Find employees of a company."""
        ...

    async def enrich_contact(self, person_name: str, domain: str) -> dict:
        """Enrich contact information for a person."""
        ...

    async def fetch_rss_entries(self, url: str) -> list[dict]:
        """Fetch RSS feed entries from a URL."""
        ...

    async def fetch_jobs(self, company: str) -> list[dict]:
        """Fetch job postings for a company."""
        ...
