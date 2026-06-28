import httpx
from typing import Any
from core.settings import settings
from core.logging import logger
from services.api_providers.base import BaseAPIProvider

class ApifyLinkedInProvider(BaseAPIProvider):
    """
    Provider for Apify LinkedIn Profile Search actor.
    Because of strict rate limits, this provider uses the synchronous 
    'run-sync-get-dataset' endpoint to avoid multiple polling calls.
    """
    
    BASE_URL = "https://api.apify.com/v2/acts/harvestapi~linkedin-profile-search/run-sync-get-dataset-items"

    async def fetch_entries(self, config: dict[str, Any]) -> list[dict[str, Any]]:
        api_key = settings.APIFY_API_TOKEN
        if not api_key:
            logger.warning("APIFY_API_TOKEN is not set. Cannot fetch Apify LinkedIn profiles.")
            return []
            
        # Ensure we have a payload to send. The config itself acts as the payload.
        # Fallback to extracting from a generic 'payload' key if the frontend wraps it.
        payload = config.get("payload", config)
        
        # If no search query is present, it's an invalid configuration
        if not payload.get("searchQuery"):
            logger.warning("No searchQuery provided in the Apify configuration.")
            return []

        params = {
            "token": api_key
        }

        try:
            # Note: Apify synchronous dataset fetch might take a long time to run 
            # (sometimes minutes for scraping).
            # We set a high timeout (e.g., 5 minutes) to ensure we don't drop the connection.
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.BASE_URL, 
                    params=params, 
                    json=payload, 
                    timeout=300.0
                )
                response.raise_for_status()
                data = response.json()
                
                entries = []
                # The returned dataset is an array of objects
                for profile in data[:3]: # Aggressive limit to protect free tier
                    entries.append({
                        # LinkedIn name / company mapping
                        "title": profile.get("fullName") or profile.get("firstName", "Unknown Person"),
                        "summary": profile.get("headline", ""),
                        "link": profile.get("url", ""),
                        "raw_data": profile
                    })
                return entries
                
        except httpx.RequestError as e:
            logger.error("Failed to connect to Apify API", error=str(e))
            return []
        except httpx.HTTPStatusError as e:
            logger.error("Apify API returned an error response", status_code=e.response.status_code, text=e.response.text)
            return []
        except Exception as e:
            logger.error("Unexpected error in Apify API provider", error=str(e))
            return []
