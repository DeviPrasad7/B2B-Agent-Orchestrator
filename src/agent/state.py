import operator
from typing import TypedDict, Annotated, Any
from pydantic import BaseModel

class ValidationNote(TypedDict):
    level: str
    message: str
    source_agent: str
    timestamp: float

def add_dict(left: dict | None, right: dict | None) -> dict:
    """Reducer for merging dictionaries instead of overwriting."""
    if left is None:
        return right or {}
    if right is None:
        return left
    return {**left, **right}

def add_list(left: list | None, right: list | None) -> list:
    """Reducer for merging lists."""
    if left is None:
        return right or []
    if right is None:
        return left
    return left + right

class GraphState(TypedDict):
    """
    The central data bus (AgentContext) for the LangGraph framework.
    Uses Annotated reducers to aggregate data from parallel execution nodes.
    """
    prospect_id: str
    current_trigger_event: str
    
    # Config loaded from database (icp, persona, thresholds)
    config: dict[str, Any]
    
    # Accumulated context data (firmographics, tech stack, raw signals)
    data: Annotated[dict[str, Any], add_dict]
    
    # Aggregated validation notes from cross-validation
    validation_notes: Annotated[list[ValidationNote], add_list]
    
    confidence_score: float
    overall_status: str
    
    human_override_payload: str | None
    
    # Tracking for circuit breaking and routing
    executed_agents: Annotated[list[str], add_list]
    errors: Annotated[list[str], add_list]
    retry_counts: Annotated[dict[str, int], add_dict]
    has_conflict: bool
    tech_detection_status: str
    next_node: str
    last_agent: str
    simulate_failure: bool
    
    # Target custom agent for the generic executor
    next_custom_agent: str

