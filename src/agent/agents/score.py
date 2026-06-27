import time
from typing import Any
from ..state import GraphState
from ..utils import Toolbox
from services.memory_service import MemoryService, MonitoringService

async def score_node(
    state: GraphState,
    toolbox: Toolbox,
    memory: MemoryService,
) -> dict[str, Any]:
    prospect_id = state.get("prospect_id", "unknown")
    try:
        signals = state.get("data", {}).get("raw_signals", [])
        
        # Keyword matching scoring
        scored = [{"signal": s, "score": 85.0} for s in signals][:20]
        
        if not scored:
            MonitoringService.log_info(prospect_id, "No signals passed filter")
            return {
                "executed_agents": ["score_node"],
                "overall_status": "NO_ACTION"
            }
        
        return {
            "executed_agents": ["score_node"],
            "data": {"scored_signals": scored},
            "confidence_score": 50.0
        }
    except Exception as e:
        MonitoringService.log_error(prospect_id, f"SCORE_ERROR: {str(e)}")
        return {"executed_agents": ["score_node"], "errors": [f"score_node: {str(e)}"], "data": {"scored_signals": []}}
