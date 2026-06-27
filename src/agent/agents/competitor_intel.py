from typing import Any
from ..state import GraphState
from ..utils import Toolbox, MemoryStore

async def competitor_intel_node(
    state: GraphState,
    toolbox: Toolbox,
    memory: MemoryStore,
) -> dict[str, Any]:
    tech_stack = state.get("data", {}).get("tech_stack", [])
    intel = {}
    for tech in tech_stack:
        name = tech.get("technology")
        comp_mapping = toolbox.get_competitor_info(name)
        if comp_mapping:
            intel[name] = comp_mapping.dict()
            
    if intel:
        return {
            "executed_agents": ["competitor_intel_node"],
            "data": {"competitor_intel": intel}
        }
    return {"executed_agents": ["competitor_intel_node"]}
