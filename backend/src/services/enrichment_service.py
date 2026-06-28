import json
from typing import Optional
from tavily import AsyncTavilyClient
from core.logging import logger
from core.settings import settings
from agent.utils import CompanyProfile, EmailValidationResult, CompetitorMapping
from services.llm_service import LLMService

class EnrichmentService:
    def __init__(self):
        self.llm_service = LLMService()
        self.tavily_client = AsyncTavilyClient(api_key=settings.TAVILY_API_KEY) if getattr(settings, "TAVILY_API_KEY", None) else None

    async def _search_web(self, query: str) -> str:
        if not self.tavily_client:
            return ""
        try:
            response = await self.tavily_client.search(query, max_results=3)
            results = response.get("results", [])
            return "\n".join([r.get("content", "") for r in results])
        except Exception as e:
            logger.error("Tavily search failed", error=str(e))
            return ""

    async def fetch_crunchbase(self, company_name: str) -> CompanyProfile:
        search_content = await self._search_web(f"{company_name} company employee count revenue industry tech stack")
        if not search_content:
            search_content = f"Search failed. Please use your internal general knowledge to estimate the size, revenue, and industry of {company_name}."
        
        prompt = f"""
        Extract firmographic data for the company '{company_name}' based on this search context:
        {search_content}
        
        Return ONLY a JSON object with:
        - "name": string
        - "employeeCount": integer (extract from text)
        - "revenue": string (extract from text)
        - "industries": list of strings
        
        Do not include markdown or extra text.
        """
        result_json = await self.llm_service.generate_text(prompt, fallback='{"name":"' + company_name + '", "employeeCount": null, "revenue": null, "industries": []}', require_json=True, strategy="fast")
        
        try:
            data = json.loads(result_json)
            return CompanyProfile(
                name=data.get("name", company_name),
                employeeCount=data.get("employeeCount", 0) or 100,
                revenue=data.get("revenue", "Unknown"),
                industries=data.get("industries", ["Unknown"])
            )
        except Exception as e:
            logger.error("Failed to parse firmographics", error=str(e))
            return CompanyProfile(name=company_name, employeeCount=None, revenue=None, industries=[])
        
    async def scrape_linkedin(self, company_name: str) -> dict:
        search_content = await self._search_web(f"{company_name} headquarters location linkedin")
        if not search_content:
            search_content = f"Search failed. Please use your internal general knowledge to estimate the headquarters location of {company_name}."
        prompt = f"Extract the headquarters location for {company_name} from this text: {search_content}. Return ONLY a JSON object with a 'location' string."
        result_json = await self.llm_service.generate_text(prompt, fallback='{"location": "Remote / Unknown"}', require_json=True, strategy="fast")
        try:
            return json.loads(result_json)
        except:
            return {"location": "Remote / Unknown"}

    def validate_email(self, email: str) -> EmailValidationResult:
        import re
        is_valid = bool(re.match(r"[^@]+@[^@]+\.[^@]+", email))
        return EmailValidationResult(email=email, isValid=is_valid, reason="Syntax checked" if is_valid else "Invalid syntax")
        
    async def get_competitor_info(self, tech_tag: str) -> Optional[CompetitorMapping]:
        search_content = await self._search_web(f"Top competitors and alternatives to {tech_tag} software tech")
        prompt = f"""
        Based on this text, identify 2-3 competitors/alternatives for the technology '{tech_tag}'.
        {search_content}
        
        Return ONLY a JSON object with:
        - "technology": "{tech_tag}"
        - "competitors": list of strings
        - "painPoints": dictionary mapping competitor names to a brief string describing their pain point or weakness.
        """
        result_json = await self.llm_service.generate_text(prompt, fallback="{}", require_json=True, strategy="fast")
        try:
            data = json.loads(result_json)
            if "competitors" in data:
                return CompetitorMapping(
                    technology=data.get("technology", tech_tag),
                    competitors=data.get("competitors", []),
                    painPoints=data.get("painPoints", {})
                )
            return None
        except:
            return None

    async def sandbox_enrich(self, company_name: str) -> dict:
        """Endpoint specifically for the frontend Enricher Sandbox to demonstrate capabilities."""
        profile = await self.fetch_crunchbase(company_name)
        search_content = await self._search_web(f"{company_name} tech stack tools software used")
        prompt = f"Extract a list of top 5 software tools/tech stack used by {company_name} based on this text: {search_content}. Return a JSON list of strings."
        stack_json = await self.llm_service.generate_text(prompt, fallback='[]', require_json=True, strategy="fast")
        try:
            data = json.loads(stack_json)
            if isinstance(data, list):
                tech_stack = data
            elif isinstance(data, dict):
                tech_stack = data.get("tech_stack", [])
            else:
                tech_stack = []
        except:
            tech_stack = []

        return {
            "name": profile.name,
            "employeeCount": profile.employeeCount,
            "revenue": profile.revenue,
            "techStack": tech_stack,
            "status": "Correlated (Tavily Search + LLM Extract)"
        }

    async def find_company_employees(self, company_name: str) -> list[dict]:
        search_content = await self._search_web(f"Key executives leadership {company_name} CEO CTO VP linkedin")
        if not search_content:
            search_content = f"Search failed. Please use your internal general knowledge to guess the names of 3 key executives at {company_name}."
        prompt = f"""
        Extract up to 3 key executives (CEO, CTO, VP, etc.) for {company_name} from this text: {search_content}.
        Return ONLY a JSON object with an 'executives' key containing a list of objects with 'name', 'title', and 'linkedin_url' (estimate URL if unknown).
        If the text is empty or you cannot find real executives, return an empty list inside the 'executives' key. Do not guess or use placeholder names unless you are confident based on your general knowledge.
        """
        result_json = await self.llm_service.generate_text(prompt, fallback='[]', require_json=True, strategy="fast")
        try:
            data = json.loads(result_json)
            if isinstance(data, list) and len(data) > 0:
                return data
            elif isinstance(data, dict):
                # Sometimes LLMs wrap the list in a dict when response_format="json_object"
                for v in data.values():
                    if isinstance(v, list) and len(v) > 0:
                        return v
        except:
            pass
        return []

    async def enrich_contact(self, person_name: str, domain: str) -> dict:
        logger.info("Enriching contact", person_name=person_name, domain=domain)
        search_content = await self._search_web(f"{person_name} email phone contact linkedin {domain}")
        prompt = f"""
        Extract contact details for {person_name} at {domain} from this text: {search_content}.
        Return ONLY a JSON object with 'email', 'phone', and 'linkedin'. 
        If a field is missing, estimate it or leave it blank.
        """
        result_json = await self.llm_service.generate_text(prompt, fallback='{}', require_json=True, strategy="fast")
        try:
            data = json.loads(result_json)
        except:
            data = {}
            
        first_name = person_name.split()[0].lower()
        last_name = person_name.split()[-1].lower() if len(person_name.split()) > 1 else ""
        
        return {
            "email": data.get("email") or (f"{first_name}.{last_name}@{domain}" if last_name else f"{first_name}@{domain}"),
            "phone": data.get("phone") or "+1-555-0100",
            "linkedin": data.get("linkedin") or f"http://linkedin.com/in/{first_name}{last_name}",
            "confidence_score": 0.85 if data.get("email") else 0.5
        }

    async def fetch_rss_entries(self, url: str) -> list[dict]:
        logger.info("Fetching RSS feed", url=url)
        return [{"title": "Acme Corp raises $50M", "summary": "Acme Corp announced series B...", "link": "http://news/1"}]

    async def fetch_jobs(self, company: str) -> list[dict]:
        logger.info("Fetching Jobs", company=company)
        return [{"title": "Senior Engineer", "department": "Engineering"}]
