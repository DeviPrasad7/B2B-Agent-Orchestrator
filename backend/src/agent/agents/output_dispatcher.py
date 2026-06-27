from typing import Any
from core.logging import logger
from ..state import GraphState
from ..utils import Toolbox
from services.memory_service import MemoryService
from ..base import AgentNode
from ..registry import register_agent

@register_agent("output_dispatcher_node", description="Sends final data (Do this after HITL APPROVED)")
class OutputDispatcherNode(AgentNode):
    def __init__(self, toolbox: Toolbox, memory: MemoryService, config: dict):
        self.toolbox = toolbox
        self.memory = memory
        self.config = config

    async def __call__(self, state: GraphState) -> dict[str, Any]:
        prospect_id = state.get("prospect_id", "unknown")
        try:
            # We want to properly handle the approval
            overall_status = state.get("overall_status", "PENDING")
            
            # Since this is the output node, if we reached here, the prospect is effectively completed or approved.
            if overall_status not in ["COMPLETED", "APPROVED"]:
                overall_status = "APPROVED"
                
            export_record = {
                "prospect_id": prospect_id, 
                "summary": state.get("data", {}).get("summary_object"), 
                "status": overall_status
            }
            
            if prospect_id != "unknown":
                event_hash = f"output_{prospect_id}"
                await self.memory.mark_event_processed(event_hash, prospect_id)
            
            # Build an updated state copy with the correct status for persistence.
            # Do NOT mutate the incoming state dict – return the update dict for
            # LangGraph to merge via its state reducers.
            updated_state = {**state, "overall_status": overall_status}
            await self.memory.save_prospect_state(updated_state)
            
            self.toolbox.emit_event("PROSPECT_COMPLETED", export_record)
            self.toolbox.send_webhook("http://example.com/webhook", export_record)
            
            return {
                "executed_agents": ["output_dispatcher_node"],
                "overall_status": overall_status
            }
        except Exception as e:
            logger.error("output_dispatcher_node failed", error=str(e), exc_info=True)
            if prospect_id != "unknown":
                await self.memory.rollback_prospect_state(prospect_id)
            return {
                "executed_agents": ["output_dispatcher_node"], 
                "overall_status": "FAILED", 
                "errors": [f"output_dispatcher_node: {str(e)}"]
            }
