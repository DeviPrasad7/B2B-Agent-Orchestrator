import json
import asyncio
from typing import Any, List
from abc import ABC, abstractmethod
from langchain_community.tools.tavily_search import TavilySearchResults

from ..state import GraphState
from ..utils import Toolbox
from services.memory_service import MemoryService
from ..base import AgentNode
from ..registry import register_agent

# ==========================================
# Interface Segregation & Dependency Inversion
# ==========================================
class ISearchClient(ABC):
    @abstractmethod
    async def search_company_info(self, company_name: str) -> str:
        """Fetch general market info and news about the company."""
        pass
    
    @abstractmethod
    async def find_competitors(self, company_name: str) -> List[str]:
        """Identify top competitors for the company."""
        pass

# ==========================================
# Concrete Implementation (Tavily)
# ==========================================
class TavilySearchClient(ISearchClient):
    def __init__(self):
        # LangChain's Tavily tool automatically picks up TAVILY_API_KEY from env
        self.search_tool = TavilySearchResults(max_results=3)

    async def search_company_info(self, company_name: str) -> str:
        query = f"{company_name} company overview, recent news, and target market"
        try:
            results = await asyncio.to_thread(self.search_tool.invoke, {"query": query})
            if isinstance(results, list):
                return "\n".join([f"- {r.get('content', '')}" for r in results])
            return str(results)
        except Exception as e:
            return f"Error fetching market info: {str(e)}"

    async def find_competitors(self, company_name: str) -> List[str]:
        query = f"top competitors and alternatives to {company_name}"
        try:
            results = await asyncio.to_thread(self.search_tool.invoke, {"query": query})
            if isinstance(results, list):
                combined = " ".join([r.get('content', '') for r in results])
                return [combined]
            return [str(results)]
        except Exception as e:
            return []

@register_agent("researcher_node", description="Uses Internet Data (Tavily API) to find company context and top competitors")
class ResearcherNode(AgentNode):
    def __init__(self, toolbox: Toolbox, memory: MemoryService, config: dict):
        self.toolbox = toolbox
        self.memory = memory
        self.config = config
        self.search_client = TavilySearchClient()

    async def __call__(self, state: GraphState) -> dict[str, Any]:
        company_name = state.get("data", {}).get("company_name") or state.get("prospect_id", "Unknown")
        
        # 1. Fetch Context
        market_context = await self.search_client.search_company_info(company_name)
        
        # 2. Fetch Competitors
        competitors_raw = await self.search_client.find_competitors(company_name)
        
        # In a full implementation, we might pass competitors_raw to an LLM to parse into a clean list.
        # For now, we'll store the raw text and let the orchestrator / summarizer handle it.
        
        return {
            "data": {
                "market_context": market_context,
                "competitors_context": competitors_raw[0] if competitors_raw else "None found",
                # Mock parsed list for UI until Summarizer processes it
                "competitors": ["Searching via Tavily...", "Analyzing market landscape..."] 
            },
            "recent_thoughts": [json.dumps({
                "type": "action",
                "agent": "ResearcherBot",
                "message": f"Searched the web for '{company_name}' using Tavily. Found market context and competitor signals."
            })],
            "executed_agents": ["researcher_node"]
        }
