import time
from typing import Any
from langgraph.types import interrupt
from ..state import GraphState, ValidationNote
from ..utils import Toolbox
from services.memory_service import MemoryService
from ..utils import MonitoringService
from ..base import AgentNode
from ..registry import register_agent

@register_agent("hitl_gateway_node", description="Pauses for human review (Do this after summarizer, or if confidence is low)")
class HitlGatewayNode(AgentNode):
    def __init__(self, toolbox: Toolbox, memory: MemoryService, config: dict):
        self.toolbox = toolbox
        self.memory = memory
        self.config = config

    async def __call__(self, state: GraphState) -> dict[str, Any]:
        prospect_id = state.get("prospect_id", "unknown")
        confidence = state.get("confidence_score", 100.0)
        conflict = state.get("has_conflict", False)
        website = state.get("data", {}).get("website_url")

        # Prefer fresh per-workflow thresholds from state (injected by WorkflowService),
        # fall back to startup snapshot in self.config.
        state_thresholds = state.get("config", {}).get("thresholds", {})
        raw_threshold = (
            state_thresholds.get("hitl_confidence_threshold")
            or self.config.get("thresholds", {}).get("hitl_confidence_threshold")
            or self.config.get("hitl_confidence_threshold")
            or 0.40
        )
        threshold = raw_threshold / 100.0 if raw_threshold > 1 else raw_threshold

        raw_auto_approve = (
            state_thresholds.get("auto_approve_threshold")
            or self.config.get("thresholds", {}).get("auto_approve_threshold")
            or self.config.get("auto_approve_threshold")
            or 0.85
        )
        auto_threshold = raw_auto_approve / 100.0 if raw_auto_approve > 1 else raw_auto_approve

        needs_hitl = False
        hitl_reason = ""
        auto_approved = False

        if not website:
            needs_hitl = True
            hitl_reason = "Missing website_url"
        elif confidence < threshold or conflict:
            needs_hitl = True
            hitl_reason = f"Low confidence ({confidence:.2f} < {threshold:.2f}) or data conflict"
        else:
            # Pause for final review if we made it to the end, unless confidence is high enough
            if state.get("data", {}).get("summary_object"):
                if confidence >= auto_threshold:
                    auto_approved = True
                else:
                    needs_hitl = True
                    hitl_reason = f"Final review (confidence {confidence:.2f} < auto-approve {auto_threshold:.2f})"
                
        updates = {"executed_agents": ["hitl_gateway_node"]}
        
        if auto_approved:
            updates["overall_status"] = "APPROVED"
            updates["validation_notes"] = [ValidationNote(level="INFO", message=f"Auto-approved (confidence {confidence:.2f} >= {auto_threshold:.2f})", source_agent="hitl", timestamp=time.time())]
            
        elif needs_hitl:
            self.toolbox.emit_event("HITL_REQUEST", {"prospect_id": prospect_id, "reason": hitl_reason})
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
