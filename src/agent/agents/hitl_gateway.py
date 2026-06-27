import time
from typing import Any
from langgraph.types import interrupt
from ..state import GraphState, ValidationNote
from ..utils import Toolbox
from services.memory_service import MemoryService, MonitoringService

async def hitl_gateway_node(
    state: GraphState,
    toolbox: Toolbox,
    memory: MemoryService,
) -> dict[str, Any]:
    prospect_id = state.get("prospect_id", "unknown")
    confidence = state.get("confidence_score", 100.0)
    conflict = state.get("has_conflict", False)
    website = state.get("data", {}).get("website_url")
    
    needs_hitl = False
    hitl_reason = ""
    
    if not website:
        needs_hitl = True
        hitl_reason = "Missing website_url"
    elif confidence < 0.40 or conflict:
        needs_hitl = True
        hitl_reason = "Low confidence or data conflict"
    else:
        # Also always pause for final review if we made it to the end
        if state.get("data", {}).get("summary_object"):
            needs_hitl = True
            hitl_reason = "Final manual review requested"
            
    updates = {"executed_agents": ["hitl_gateway_node"]}
    
    if needs_hitl:
        toolbox.emit_event("HITL_REQUEST", {"prospect_id": prospect_id, "reason": hitl_reason})
        # Pause execution using LangGraph's inline interrupt
        # The user will resume with Command(resume={"action": "APPROVED", ...})
        response = interrupt({"prospect_id": prospect_id, "reason": hitl_reason, "state_snapshot": state})
        
        if response:
            action = response.get("action")
            if action in ["APPROVED", "EDITED"]:
                updates["overall_status"] = "APPROVED" if action == "APPROVED" else "EDITED"
            elif action == "REJECTED":
                updates["overall_status"] = "REJECTED"
            elif action == "TIMEOUT":
                updates["overall_status"] = "TIMEOUT"
            
            # Apply any edits to data
            if "edits" in response:
                updates["data"] = response["edits"]
                
            updates["human_override_payload"] = str(response)
            updates["validation_notes"] = [ValidationNote(level="INFO", message=f"Human intervention: {action}", source_agent="hitl", timestamp=time.time())]

    return updates
