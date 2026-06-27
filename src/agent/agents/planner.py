import json
from typing import Any
from ..state import GraphState
from ..utils import Toolbox
from services.memory_service import MemoryService
from ..utils import MonitoringService

async def planner_node(
    state: GraphState,
    toolbox: Toolbox,
    memory: MemoryService,
) -> dict[str, Any]:
    prospect_id = state.get("prospect_id", "unknown")
    executed_agents = state.get("executed_agents", [])
    overall_status = state.get("overall_status", "PENDING")
    
    if overall_status in ["NO_ACTION", "REJECTED", "TIMEOUT", "APPROVED", "COMPLETED"]:
        return {"next_node": "__end__"}
        
    available_agents = [
        "monitor_node",
        "score_node",
        "tech_stack_detector_node",
        "enricher_node",
        "competitor_intel_node",
        "cross_validator_node",
        "persona_matcher_node",
        "contact_finder_node",
        "summarizer_node",
        "hitl_gateway_node",
        "output_dispatcher_node"
    ]
    
    prompt = f"""
You are the Planner Agent for a B2B SaaS Customer Discovery pipeline.
Your job is to decide the next agent to execute based on the current state.

Available Agents:
- monitor_node: Fetches trigger events (Do this first if raw_signals is empty)
- score_node: Scores the company against ICP (Do this after monitor)
- tech_stack_detector_node: Detects technologies (Do this after scoring if we should proceed)
- enricher_node: Enriches firmographics
- competitor_intel_node: Finds competitor info (Optional, requires tech stack)
- cross_validator_node: Validates data consistency
- persona_matcher_node: Finds target personas (Do this after validation)
- contact_finder_node: Finds contact info for personas (Do this after persona matcher)
- summarizer_node: Creates final summary (Do this when all data is gathered)
- hitl_gateway_node: Pauses for human review (Do this after summarizer, or if confidence is low)
- output_dispatcher_node: Sends final data (Do this after HITL APPROVED)

Current State Summary:
- Executed Agents: {executed_agents}
- Overall Status: {overall_status}
- Has Company Name: {bool(state.get('data', {}).get('company_name'))}
- Has Summary: {bool(state.get('data', {}).get('summary_object'))}

Output ONLY a JSON object with a single key "next_node" containing the exact name of the next agent to run. If the workflow is complete, output "__end__".
"""
    
    fallback = '{"next_node": "__end__"}'
    
    try:
        response = await toolbox.generate_text(prompt, fallback)
        import re
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group(0))
            next_node = data.get("next_node", "__end__")
        else:
            next_node = "__end__"
            
        if next_node not in available_agents and next_node != "__end__":
            next_node = "__end__"
            
        return {"executed_agents": ["planner_node"], "next_node": next_node}
    except Exception as e:
        MonitoringService.log_error(prospect_id, f"PLANNER_ERROR: {str(e)}")
        return {"next_node": "hitl_gateway_node"} # Fallback to human if planner fails
