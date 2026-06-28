import time
from typing import Any
from ..state import GraphState
from ..utils import Toolbox, CircuitBreakerState
from services.memory_service import MemoryService
from ..base import AgentNode
from ..registry import register_agent

@register_agent("enricher_node", description="Enriches firmographics")
class EnricherNode(AgentNode):
    def __init__(self, toolbox: Toolbox, memory: MemoryService, config: dict):
        self.toolbox = toolbox
        self.memory = memory
        self.config = config

    async def __call__(self, state: GraphState) -> dict[str, Any]:
        prospect_id = state.get("prospect_id", "unknown")
        company_name = state.get("data", {}).get("company_name", prospect_id)
        try:
            cb_state = self.toolbox.circuit_breaker.check_health("CRUNCHBASE_API")
            
            firmographics = {}
            data_sources = {}
            
            if cb_state != CircuitBreakerState.OPEN:
                cb_data = await self.toolbox.fetch_crunchbase(company_name)
                firmographics["name"] = cb_data.name
                firmographics["employeeCount"] = cb_data.employeeCount
                firmographics["revenue"] = cb_data.revenue
                firmographics["industries"] = cb_data.industries
                data_sources["crunchbase"] = "success"
                self.toolbox.circuit_breaker.record_success("CRUNCHBASE_API")
                
            li_data = await self.toolbox.scrape_linkedin(company_name)
            firmographics["location"] = li_data.get("location")
            data_sources["linkedin"] = "success"
            
            return {
                "executed_agents": ["enricher_node"],
                "data": {
                    "firmographics": firmographics,
                    "data_sources": data_sources,
                    "employee_count": firmographics.get("employeeCount"),
                    "revenue": firmographics.get("revenue"),
                }
            }
        except Exception as e:
            self.toolbox.circuit_breaker.record_failure("CRUNCHBASE_API")
            return {"executed_agents": ["enricher_node"], "errors": [f"enricher_node: {str(e)}"], "data": {"firmographics": {}}}
