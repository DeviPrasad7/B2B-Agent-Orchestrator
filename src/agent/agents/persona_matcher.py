import time
from typing import Any
from ..state import GraphState
from ..utils import Toolbox
from services.memory_service import MemoryService
from ..utils import MonitoringService

async def persona_matcher_node(
    state: GraphState,
    toolbox: Toolbox,
    memory: MemoryService,
) -> dict[str, Any]:
    prospect_id = state.get("prospect_id", "unknown")
    company_name = state.get("data", {}).get("company_name")
    
    if not company_name:
        return {"executed_agents": ["persona_matcher_node"]}
        
    try:
        persona_def = state.get("config", {}).get("persona", {})
        job_titles = persona_def.get("job_titles", [])
            
        employees = await toolbox.find_company_employees(company_name)
        
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
                
        return {
            "executed_agents": ["persona_matcher_node"],
            "data": {"personas": matched[:3]}
        }
    except Exception as e:
        MonitoringService.log_error(prospect_id, f"PERSONA_ERROR: {str(e)}")
        return {"executed_agents": ["persona_matcher_node"], "errors": [f"persona_matcher_node: {str(e)}"]}
