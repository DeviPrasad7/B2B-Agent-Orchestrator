import httpx
from typing import Any
from core.settings import settings
from core.logging import logger
from services.api_providers.base import BaseAPIProvider

class NewsAPIProvider(BaseAPIProvider):
    """
    Provider for News API (newsapi.org).
    Fetches articles based on keywords.
    """
    
    BASE_URL = "https://newsapi.org/v2/everything"

    async def fetch_entries(self, config: dict[str, Any]) -> list[dict[str, Any]]:
        api_key = settings.NEWS_API_KEY
        if not api_key:
            logger.warning("NEWS_API_KEY is not set. Cannot fetch News API entries.")
            return []
            
        keywords = config.get("keywords")
        if not keywords:
            logger.warning("No keywords provided for News API search.")
            return []

        # Sometimes frontend might pass 'url' instead of 'keywords' based on our generic config form, handle that gracefully:
        if isinstance(keywords, str) and keywords.startswith("http"):
             # If url was wrongly mapped to keywords
             pass 

        params = {
            "q": keywords,
            "apiKey": api_key,
            "sortBy": "publishedAt",
            "pageSize": 10  # Limiting the number to prevent flooding
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(self.BASE_URL, params=params, timeout=10.0)
                response.raise_for_status()
                data = response.json()
                
                entries = []
                for article in data.get("articles", []):
                    # Filter out "[Removed]" articles
                    if article.get("title") == "[Removed]":
                        continue
                        
                    entries.append({
                        "title": article.get("title", "Unknown Title"),
                        "summary": article.get("description", ""),
                        "link": article.get("url", ""),
                        "raw_data": article
                    })
                return entries
                
        except httpx.RequestError as e:
            logger.error("Failed to connect to News API", error=str(e))
            return []
        except httpx.HTTPStatusError as e:
            logger.error("News API returned an error response", status_code=e.response.status_code, text=e.response.text)
            return []
        except Exception as e:
            logger.error("Unexpected error in News API provider", error=str(e))
            return []
