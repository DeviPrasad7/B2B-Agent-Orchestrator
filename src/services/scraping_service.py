import time
import httpx
from bs4 import BeautifulSoup
from core.logging import logger
from agent.utils import WebPage, TechStackEntry, JobPosting
from core.exceptions import RateLimitError, TimeoutError, ServiceUnavailableError

class ScrapingService:
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
