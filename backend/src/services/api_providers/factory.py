from typing import Optional
from core.logging import logger
from services.api_providers.base import BaseAPIProvider
from services.api_providers.news_api import NewsAPIProvider
from services.api_providers.generic_api import GenericAPIProvider
from services.api_providers.github_api import GitHubAPIProvider
from services.api_providers.apify_api import ApifyLinkedInProvider

class APIProviderFactory:
    """
    Factory to retrieve the appropriate API provider for a given trigger source type.
    Adheres to the Open/Closed Principle (OCP).
    """
    
    def __init__(self):
        self._providers: dict[str, BaseAPIProvider] = {
            "news_api": NewsAPIProvider(),
            "generic_api": GenericAPIProvider(),
            "github_api": GitHubAPIProvider(),
            "apify_linkedin": ApifyLinkedInProvider(),
        }

    def register_provider(self, source_type: str, provider: BaseAPIProvider) -> None:
        """Register a new API provider."""
        self._providers[source_type] = provider

    def get_provider(self, source_type: str) -> Optional[BaseAPIProvider]:
        """Get the provider for a specific source type."""
        provider = self._providers.get(source_type)
        if not provider:
            logger.warning(f"No API provider registered for source type: {source_type}")
        return provider
