from typing import Any
from ..state import GraphState
from ..utils import Toolbox
from services.memory_service import MemoryService
from ..base import AgentNode
from ..registry import register_agent

@register_agent("consolidation_node", description="Node used strictly to converge parallel flows")
class ConsolidationNode(AgentNode):
    def __init__(self, toolbox: Toolbox, memory: MemoryService, config: dict):
        self.toolbox = toolbox
        self.memory = memory
        self.config = config

    async def __call__(self, state: GraphState) -> dict[str, Any]:
        # Merge validation notes or resolve conflicting statuses here
        return {"executed_agents": ["consolidation_node"]}
