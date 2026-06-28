import httpx
import os
from typing import Any
from core.logging import logger
from services.api_providers.base import BaseAPIProvider

class GenericAPIProvider(BaseAPIProvider):
    """
    A generic provider for unspecified future APIs.
    Expects the TriggerSource config to provide the base_url, method, 
    and the name of the environment variable containing the API key.
    """

    async def fetch_entries(self, config: dict[str, Any]) -> list[dict[str, Any]]:
        # This generic implementation will look for basic config instructions:
        # { "url": "...", "api_key_env_var": "SOME_KEY", "query_params": {} }
        
        url = config.get("url")
        if not url:
            logger.warning("Generic API Provider called without a URL in config.")
            return []
            
        api_key_env_var = config.get("api_key_env_var")
        headers = config.get("headers", {})
        params = config.get("query_params", {})
        
        if api_key_env_var:
            api_key = os.getenv(api_key_env_var)
            if not api_key:
                logger.warning(f"API key env var '{api_key_env_var}' not found in environment.")
                return []
            
            # Convention: if API key is provided, we usually pass it in Authorization header 
            # as Bearer token, or specific header. This can be overridden in config.
            auth_header_name = config.get("auth_header_name", "Authorization")
            if auth_header_name == "Authorization" and "Bearer" not in api_key:
                 headers[auth_header_name] = f"Bearer {api_key}"
            else:
                 headers[auth_header_name] = api_key
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params, headers=headers, timeout=15.0)
                response.raise_for_status()
                data = response.json()
                
                # Standardize the output. If the response is a list, map it.
                # If it's a dict, try to find an array field.
                entries = []
                items = []
                
                data_path = config.get("data_path")
                if data_path and isinstance(data, dict):
                    # e.g., "data.results"
                    keys = data_path.split(".")
                    curr = data
                    for k in keys:
                        curr = curr.get(k, {})
                    if isinstance(curr, list):
                        items = curr
                elif isinstance(data, list):
                    items = data
                elif isinstance(data, dict):
                     # Best effort guess
                     for k, v in data.items():
                         if isinstance(v, list):
                             items = v
                             break

                # Mapping logic
                title_key = config.get("title_key", "title")
                summary_key = config.get("summary_key", "summary")
                link_key = config.get("link_key", "link")
                
                for item in items[:3]: # Aggressive limit to protect free tier
                    if not isinstance(item, dict):
                        continue
                    entries.append({
                        "title": item.get(title_key, "Unknown Event"),
                        "summary": item.get(summary_key, ""),
                        "link": item.get(link_key, ""),
                        "raw_data": item
                    })
                    
                return entries
                
        except Exception as e:
            logger.error("Error in Generic API provider", error=str(e), url=url)
            return []
