from typing import Any
from ..state import GraphState
from ..utils import Toolbox, MemoryStore, MonitoringService

async def output_dispatcher_node(
    state: GraphState,
    toolbox: Toolbox,
    memory: MemoryStore,
) -> dict[str, Any]:
    prospect_id = state.get("prospect_id", "unknown")
    try:
        export_record = {"prospect_id": prospect_id, "summary": state.get("data", {}).get("summary_object"), "status": state.get("overall_status")}
        
        event_hash = f"output_{prospect_id}"
        memory.mark_event_processed(event_hash, prospect_id)
        memory.save_prospect_state(prospect_id, state)
        
        toolbox.emit_event("PROSPECT_COMPLETED", export_record)
        toolbox.send_webhook("http://example.com/webhook", export_record)
        
        MonitoringService.log_success(prospect_id, "Execution completed successfully.")
        return {
            "executed_agents": ["output_dispatcher_node"]
        }
    except Exception as e:
        MonitoringService.log_error(prospect_id, "OUTPUT_FAILED")
        memory.rollback_prospect_state(prospect_id)
        return {"executed_agents": ["output_dispatcher_node"], "overall_status": "FAILED", "errors": [f"output_dispatcher_node: {str(e)}"]}

async def consolidation_node(
    state: GraphState,
    toolbox: Toolbox,
    memory: MemoryStore,
) -> dict[str, Any]:
    """Node used strictly to converge parallel flows."""
    return {}
