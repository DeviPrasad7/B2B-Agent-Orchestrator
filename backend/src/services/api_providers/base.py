from abc import ABC, abstractmethod
from typing import Any

class BaseAPIProvider(ABC):
    """
    Abstract base class for all external API trigger providers.
    Adheres to the Dependency Inversion Principle (DIP).
    """
    
    @abstractmethod
    async def fetch_entries(self, config: dict[str, Any]) -> list[dict[str, Any]]:
        """
        Fetch entries from the underlying API.
        
        Args:
            config: A dictionary containing configuration specific to the provider 
                   (e.g., keywords, search terms, base URL overrides).
                   
        Returns:
            A list of dictionary objects representing the raw events.
            Each event should ideally contain 'title', 'summary', and 'link' keys,
            though specific structures may vary by provider.
        """
        pass
