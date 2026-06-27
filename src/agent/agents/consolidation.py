from typing import Any
from ..state import GraphState
from ..utils import Toolbox
from services.memory_service import MemoryService

async def consolidation_node(
    state: GraphState,
    toolbox: Toolbox,
    memory: MemoryService,
) -> dict[str, Any]:
    """Node used strictly to converge parallel flows."""
    return {}
