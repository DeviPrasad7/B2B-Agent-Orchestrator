"""
ConsolidationNode – persists the current workflow state to the DB.

Used as a convergence point after parallel branches (if any) and as an
explicit checkpoint mid-pipeline. The LLM planner description is intentionally
brief so the planner only invokes it when explicitly needed.
"""
from typing import Any

from ..base import AgentNode
from ..registry import register_agent
from ..state import GraphState
from ..utils import Toolbox
from services.memory_service import MemoryService


@register_agent(
    "consolidation_node",
    description="Persists current state to DB as a mid-pipeline checkpoint (only needed after parallel branches)",
)
class ConsolidationNode(AgentNode):
    def __init__(self, toolbox: Toolbox, memory: MemoryService, config: dict) -> None:
        self.toolbox = toolbox
        self.memory = memory
        self.config = config

    async def __call__(self, state: GraphState) -> dict[str, Any]:
        """Save state snapshot to the DB and return a minimal update dict."""
        try:
            await self.memory.save_prospect_state(dict(state))
        except Exception:
            pass  # Non-fatal – checkpoint failure should not break the pipeline
        return {"executed_agents": ["consolidation_node"]}
