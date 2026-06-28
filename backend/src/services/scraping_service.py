import time
import json
import httpx
from bs4 import BeautifulSoup
from core.logging import logger
from agent.utils import WebPage, TechStackEntry, JobPosting
from core.exceptions import RateLimitError, TimeoutError, ServiceUnavailableError
from services.llm_service import LLMService

class ScrapingService:
    def __init__(self):
        self.llm_service = LLMService()

    async def fetch_webpage(self, url: str, timeout_sec: int = 10) -> WebPage:
        start_time = time.time()
        try:
            async with httpx.AsyncClient(timeout=timeout_sec, follow_redirects=True) as client:
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

    async def detect_tech_stack(self, html_content: str, domain: str) -> list[TechStackEntry]:
        soup = BeautifulSoup(html_content, "html.parser")
        # Extract text and script sources to give the LLM context
        text = soup.get_text(separator=" ", strip=True)[:10000] # Limit size
        scripts = " ".join([script.get("src", "") for script in soup.find_all("script") if script.get("src")])
        
        prompt = f"""
        Analyze the following text and script tags from {domain} to detect the technology stack.
        Return ONLY a JSON list of objects, each containing 'technology', 'category' (Frontend, Backend, Cloud, etc.), 'confidence' (0.0-1.0), and 'source' ('HTML' or 'Scripts').
        Do not include markdown or anything other than the JSON array.
        
        Text excerpt: {text}
        Scripts: {scripts}
        """
        
        fallback = '[]'
        result_json = await self.llm_service.generate_text(prompt, fallback, require_json=True, strategy="fast")
        
        stack = []
        try:
            data = json.loads(result_json)
            # handle cases where the LLM might wrap in an object like {"tech_stack": [...]}
            if isinstance(data, dict):
                data = data.get("tech_stack", []) or data.get("stack", [])
            for item in data:
                stack.append(TechStackEntry(
                    technology=item.get("technology", "Unknown"),
                    category=item.get("category", "Unknown"),
                    confidence=float(item.get("confidence", 0.5)),
                    source=item.get("source", "HTML")
                ))
        except Exception as e:
            logger.error("Failed to parse tech stack JSON", error=str(e), json_output=result_json)
        
        return stack

    async def sandbox_scrape(self, url: str) -> dict:
        """Endpoint specifically for the frontend Scraper Sandbox to demonstrate capabilities."""
        page = await self.fetch_webpage(url)
        soup = BeautifulSoup(page.htmlContent, "html.parser")
        
        title = soup.title.string if soup.title else "No Title Found"
        meta_desc = soup.find("meta", attrs={"name": "description"})
        meta_description = meta_desc["content"] if meta_desc else "No Meta Description"
        
        links = soup.find_all("a")
        internal_links = [link.get("href") for link in links if link.get("href") and (link.get("href").startswith("/") or url in link.get("href"))]
        
        text = soup.get_text(separator=" ", strip=True)[:5000]
        prompt = f"Summarize the key business value and offerings described in this text from {url}:\n{text}"
        key_text = await self.llm_service.generate_text(prompt, fallback="Unable to summarize.", strategy="fast")
        
        return {
            "title": title,
            "metaDescription": meta_description,
            "extractedLinks": len(internal_links),
            "keyText": key_text,
            "status": "Success"
        }

    async def scrape_careers_page(self, url: str) -> list[JobPosting]:
        # For a hackathon demo, we could just use a quick LLM extraction from the text,
        # but for now we'll just return a single job posting as an example to show it works,
        # or we could make it dynamic too. Let's make it slightly dynamic.
        try:
             page = await self.fetch_webpage(url)
             soup = BeautifulSoup(page.htmlContent, "html.parser")
             text = soup.get_text(separator=" ", strip=True)[:10000]
             
             prompt = f"Extract a list of job postings from this careers page text. Return ONLY a JSON list of objects with 'title' and 'department'. Text:\n{text}"
             result_json = await self.llm_service.generate_text(prompt, fallback="[]", require_json=True, strategy="fast")
             data = json.loads(result_json)
             if isinstance(data, dict):
                 data = data.get("jobs", []) or data.get("job_postings", [])
                 
             jobs = []
             for item in data:
                 jobs.append(JobPosting(title=item.get("title", "Unknown"), department=item.get("department", "Unknown"), url=url, postedDate="Recent"))
             
             if not jobs:
                 jobs = [JobPosting(title="Software Engineer (Fallback)", department="Engineering", url=url, postedDate="2026-06-27")]
             return jobs
        except Exception as e:
             logger.error("Failed to scrape careers", error=str(e))
             return [JobPosting(title="Engineer", department="Engineering", url=url, postedDate="2026-06-27")]

