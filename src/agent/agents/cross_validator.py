import time
from typing import Any
from ..state import GraphState, ValidationNote
from ..utils import Toolbox
from services.memory_service import MemoryService, MonitoringService

async def cross_validator_node(
    state: GraphState,
    toolbox: Toolbox,
    memory: MemoryService,
) -> dict[str, Any]:
    prospect_id = state.get("prospect_id", "unknown")
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
