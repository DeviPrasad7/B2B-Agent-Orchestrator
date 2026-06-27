import time
from typing import Any
from ..state import GraphState, ValidationNote
from ..utils import Toolbox, CircuitBreakerState, MonitoringService
from services.memory_service import MemoryService
from ..base import AgentNode
from ..registry import register_agent

@register_agent("tech_stack_detector_node", description="Detects technologies (Do this after scoring if we should proceed)")
class TechStackDetectorNode(AgentNode):
    def __init__(self, toolbox: Toolbox, memory: MemoryService, config: dict):
        self.toolbox = toolbox
        self.memory = memory
        self.config = config

    async def __call__(self, state: GraphState) -> dict[str, Any]:
        prospect_id = state.get("prospect_id", "unknown")
        website_url = state.get("data", {}).get("website_url")
        if not website_url:
            return {"executed_agents": ["tech_stack_detector_node"]}
    
        try:
            cb_state = self.toolbox.circuit_breaker.check_health("TECH_DETECTION_API")
            if cb_state == CircuitBreakerState.OPEN:
                return {"executed_agents": ["tech_stack_detector_node"]}
                
            page = await self.toolbox.fetch_webpage(website_url, 10)
            stack = self.toolbox.detect_tech_stack(page.htmlContent, website_url)
            
            self.toolbox.circuit_breaker.record_success("TECH_DETECTION_API")
            return {
                "executed_agents": ["tech_stack_detector_node"],
                "data": {
                    "tech_stack": [t.model_dump() for t in stack],
                    "tech_source_map": {t.technology: t.source for t in stack}
                },
                "tech_detection_status": "SUCCESS"
            }
        except Exception as e:
            self.toolbox.circuit_breaker.record_failure("TECH_DETECTION_API")
            MonitoringService.log_warning(prospect_id, f"Website unreachable, partial data: {str(e)}")
            return {
                "executed_agents": ["tech_stack_detector_node"],
                "tech_detection_status": "PARTIAL",
                "validation_notes": [ValidationNote(level="WARN", message="Tech stack detection failed", source_agent="tech_stack", timestamp=time.time())],
                "errors": [f"tech_stack_detector_node: {str(e)}"]
            }
