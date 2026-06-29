import httpx
from typing import Any
from core.settings import settings
from core.logging import logger
from services.api_providers.base import BaseAPIProvider

class GitHubAPIProvider(BaseAPIProvider):
    """
    Provider for GitHub API.
    Supports GitHub Search API to discover repositories that match criteria.
    """
    
    SEARCH_BASE_URL = "https://api.github.com/search/repositories"

    async def fetch_entries(self, config: dict[str, Any]) -> list[dict[str, Any]]:
        api_key = getattr(settings, "GITHUB_TOKEN", None)
        
        # The frontend/config will provide the search query (e.g. 'tetris stars:>500' or 'ai-agent')
        # We can map 'keywords' or 'url' to the query 'q'
        query = config.get("keywords") or config.get("query") or config.get("url")
        if not query:
            logger.warning("No search query provided for GitHub Search API.")
            return []

        # If they provided a full URL by accident, extract the query or just use the query they provided
        if isinstance(query, str) and query.startswith("http"):
            # Simple fallback if URL is provided
            if "?q=" in query:
                query = query.split("?q=")[1].split("&")[0]

        params = {
            "q": query,
            "sort": config.get("sort", "updated"),
            "order": config.get("order", "desc"),
            "per_page": 3 # Aggressively limit results to save free-tier LLM bandwidth
        }

        headers = {
            "Accept": "application/vnd.github.v3+json"
        }
        
        if api_key:
            headers["Authorization"] = f"token {api_key}"

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(self.SEARCH_BASE_URL, params=params, headers=headers, timeout=10.0)
                response.raise_for_status()
                data = response.json()
                
                entries = []
                for repo in data.get("items", []):
                    entries.append({
                        "title": repo.get("full_name", "Unknown Repo"),
                        "summary": repo.get("description", ""),
                        "link": repo.get("html_url", ""),
                        "raw_data": repo
                    })
                return entries
                
        except httpx.RequestError as e:
            logger.error("Failed to connect to GitHub API", error=str(e))
            return []
        except httpx.HTTPStatusError as e:
            logger.error("GitHub API returned an error response", status_code=e.response.status_code, text=e.response.text)
            return []
        except Exception as e:
            logger.error("Unexpected error in GitHub API provider", error=str(e))
            return []
