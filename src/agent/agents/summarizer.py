import time
from typing import Any
from ..state import GraphState
from ..utils import Toolbox, CircuitBreakerState
from services.memory_service import MemoryService
from ..utils import MonitoringService

async def summarizer_node(
    state: GraphState,
    toolbox: Toolbox,
    memory: MemoryService,
) -> dict[str, Any]:
    prospect_id = state.get("prospect_id", "unknown")
    try:
        cb_state = toolbox.circuit_breaker.check_health("LLM_API")
        fallback_summary = '{"overview": "Fallback", "strengths": "Unknown", "risks": "Unknown", "recommendation": "Review manually"}'
        if cb_state == CircuitBreakerState.OPEN:
            MonitoringService.log_warning(prospect_id, "LLM circuit open, using fallback")
            return {
                "executed_agents": ["summarizer_node"],
                "data": {"summary_object": fallback_summary}
            }
        
        firmographics = state.get("data", {}).get("firmographics", {})
        prompt = f"Summarize this prospect: {firmographics}. Output JSON."
        summary = await toolbox.generate_text(prompt, fallback_summary)
        
        if summary == fallback_summary:
            toolbox.circuit_breaker.record_failure("LLM_API")
            MonitoringService.log_error(prospect_id, "LLM unavailable, using fallback")
        else:
            toolbox.circuit_breaker.record_success("LLM_API")
            
        return {
            "executed_agents": ["summarizer_node"],
            "data": {"summary_object": summary}
        }
    except Exception as e:
        toolbox.circuit_breaker.record_failure("LLM_API")
        return {
            "executed_agents": ["summarizer_node"],
            "data": {"summary_object": '{"overview": "Fallback", "strengths": "Unknown", "risks": "Unknown", "recommendation": "Review manually"}'},
            "errors": [f"summarizer_node: {str(e)}"]
        }
