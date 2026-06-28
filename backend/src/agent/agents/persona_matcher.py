import time
from typing import Any
from ..state import GraphState
from ..utils import Toolbox
from services.memory_service import MemoryService
from ..utils import MonitoringService
from ..base import AgentNode
from ..registry import register_agent

@register_agent("persona_matcher_node", description="Finds target personas (Do this after validation)")
class PersonaMatcherNode(AgentNode):
    def __init__(self, toolbox: Toolbox, memory: MemoryService, config: dict):
        self.toolbox = toolbox
        self.memory = memory
        self.config = config

    async def __call__(self, state: GraphState) -> dict[str, Any]:
        prospect_id = state.get("prospect_id", "unknown")
        company_name = state.get("data", {}).get("company_name")
        
        if not company_name:
            return {"executed_agents": ["persona_matcher_node"]}
            
        try:
            persona_def = self.config.get("personas", {})
            if hasattr(persona_def, "model_dump"):
                persona_def = persona_def.model_dump()
                
            if not persona_def or not isinstance(persona_def, dict):
                p_state = state.get("config", {}).get("persona", {})
                if hasattr(p_state, "model_dump"):
                    p_state = p_state.model_dump()
                persona_def = p_state if isinstance(p_state, dict) else {}
                
            job_titles = persona_def.get("job_titles", [])
                
            employees = await self.toolbox.find_company_employees(company_name)
            
            # Simple mock filtering logic based on persona titles
            target_titles = [t.lower() for t in job_titles]
            matched = []
            for emp in employees:
                emp_title = emp.get("title", "").lower()
                if any(t in emp_title for t in target_titles):
                    matched.append({
                        "name": emp.get("name"),
                        "title": emp.get("title"),
                        "linkedin_url": emp.get("linkedin_url"),
                        "confidence": 0.9
                    })
                    
            if not matched and employees:
                # Fallback to the top employees if no target persona matched
                for emp in employees[:3]:
                    matched.append({
                        "name": emp.get("name"),
                        "title": emp.get("title"),
                        "linkedin_url": emp.get("linkedin_url"),
                        "confidence": 0.5
                    })
                    
            return {
                "executed_agents": ["persona_matcher_node"],
                "data": {"personas": matched[:3]}
            }
        except Exception as e:
            MonitoringService.log_error(prospect_id, f"PERSONA_ERROR: {str(e)}")
            return {"executed_agents": ["persona_matcher_node"], "errors": [f"persona_matcher_node: {str(e)}"]}
