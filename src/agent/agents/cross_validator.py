import time
from typing import Any
from ..state import GraphState, ValidationNote
from ..utils import Toolbox
from services.memory_service import MemoryService
from ..utils import MonitoringService
from ..base import AgentNode
from ..registry import register_agent

@register_agent("cross_validator_node", description="Validates data consistency")
class CrossValidatorNode(AgentNode):
    def __init__(self, toolbox: Toolbox, memory: MemoryService, config: dict):
        self.toolbox = toolbox
        self.memory = memory
        self.config = config

    async def __call__(self, state: GraphState) -> dict[str, Any]:
        prospect_id = state.get("prospect_id", "unknown")
        try:
            firmographics = state.get("data", {}).get("firmographics", {})
            
            has_conflict = False
            notes = []
            
            # In memory cross-validation logic
            if not firmographics.get("name") or not firmographics.get("employeeCount"):
                notes.append(ValidationNote(
                    level="WARN",
                    message="Missing key firmographics (name or employeeCount)",
                    source_agent="cross_validator",
                    timestamp=time.time()
                ))
                
            confidence = 0.70 if notes else 0.95
            if notes:
                has_conflict = True
                MonitoringService.log_warning(prospect_id, "Validation issues found")
            
            return {
                "executed_agents": ["cross_validator_node"],
                "confidence_score": confidence,
                "has_conflict": has_conflict,
                "validation_notes": notes
            }
        except Exception as e:
            MonitoringService.log_error(prospect_id, f"CROSS_VALIDATOR_ERROR: {str(e)}")
            return {"executed_agents": ["cross_validator_node"], "errors": [f"cross_validator_node: {str(e)}"]}
