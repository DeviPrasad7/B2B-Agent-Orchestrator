from typing import Any
from ..state import GraphState
from ..utils import Toolbox
from services.memory_service import MemoryService
from ..base import AgentNode
from ..registry import register_agent
from services.llm_service import LLMService

@register_agent("competitor_intel_node", description="Finds competitor info and generates a SWOT analysis.")
class CompetitorIntelNode(AgentNode):
    def __init__(self, toolbox: Toolbox, memory: MemoryService, config: dict):
        self.toolbox = toolbox
        self.memory = memory
        self.config = config
        self.llm = LLMService()

    async def __call__(self, state: GraphState) -> dict[str, Any]:
        prospect_id = state.get("prospect_id", "unknown")
        try:
            tech_stack = state.get("data", {}).get("tech_stack", [])
            company_name = state.get("data", {}).get("company_name", "the target company")
            
            # Fetch standard tech mapping
            intel = {}
            for tech in tech_stack:
                # tech is just a string now from enrichment_service
                name = tech if isinstance(tech, str) else tech.get("technology", "")
                if name:
                    comp_mapping = await self.toolbox.enrichment_service.get_competitor_info(name)
                    if comp_mapping:
                        intel[name] = comp_mapping.model_dump()

            # Generate SWOT
            tech_str = ", ".join(tech_stack) if tech_stack else "Unknown tech stack"
            prompt = f"""
            Act as a B2B strategy analyst. Generate a quick, insightful SWOT analysis (Strengths, Weaknesses, Opportunities, Threats) 
            for '{company_name}', a company using the following technology stack: {tech_str}.
            Keep it concise and focus on their market position and technological choices.
            """
            
            swot_analysis = await self.llm.generate_text(prompt, fallback="SWOT Analysis unavailable.", strategy="fast")

            return {
                "executed_agents": ["competitor_intel_node"],
                "data": {
                    "competitor_intel": intel,
                    "competitors_context": f"SWOT Analysis:\n{swot_analysis}\n\nTech Competitors: {list(intel.keys())}"
                }
            }
        except Exception as e:
            from core.logging import logger
            logger.error(f"Error in competitor_intel_node: {str(e)}", extra={"prospect_id": prospect_id})
            return {"executed_agents": ["competitor_intel_node"], "errors": [f"competitor_intel_node: {str(e)}"]}
