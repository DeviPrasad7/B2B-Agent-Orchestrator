import time
from typing import Any
from ..state import GraphState, ValidationNote
from ..utils import Toolbox, CircuitBreakerState, MonitoringService, MemoryStore

async def tech_stack_detector_node(
    state: GraphState,
    toolbox: Toolbox,
    memory: MemoryStore,
) -> dict[str, Any]:
    prospect_id = state.get("prospect_id", "unknown")
    website_url = state.get("data", {}).get("website_url")
    if not website_url:
        return {"executed_agents": ["tech_stack_detector_node"]}

    try:
        cb_state = toolbox.circuit_breaker.check_health("TECH_DETECTION_API")
        if cb_state == CircuitBreakerState.OPEN:
            return {"executed_agents": ["tech_stack_detector_node"]}
            
        page = await toolbox.fetch_webpage(website_url, 10)
        stack = toolbox.detect_tech_stack(page.htmlContent, website_url)
        
        toolbox.circuit_breaker.record_success("TECH_DETECTION_API")
        return {
            "executed_agents": ["tech_stack_detector_node"],
            "data": {
                "tech_stack": [t.dict() for t in stack],
                "tech_source_map": {t.technology: t.source for t in stack}
            },
            "tech_detection_status": "SUCCESS"
        }
    except Exception as e:
        toolbox.circuit_breaker.record_failure("TECH_DETECTION_API")
        MonitoringService.log_warning(prospect_id, f"Website unreachable, partial data: {str(e)}")
        return {
            "executed_agents": ["tech_stack_detector_node"],
            "tech_detection_status": "PARTIAL",
            "validation_notes": [ValidationNote(level="WARN", message="Tech stack detection failed", source_agent="tech_stack", timestamp=time.time())],
            "errors": [f"tech_stack_detector_node: {str(e)}"]
        }
