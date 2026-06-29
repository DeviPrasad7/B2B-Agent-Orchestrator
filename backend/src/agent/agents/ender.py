from agent.state import GraphState
from agent.registry import register_agent
from ..utils import Toolbox
from services.memory_service import MemoryService
from ..base import AgentNode
from typing import Any
import time

@register_agent("ender_node", "Consolidates data, summarizes the outcome, and evaluates HITL requirements before dispatch. This serves as a unified terminal node for workflows.")
class EnderNode(AgentNode):
    """
    Consolidates data, summarizes the outcome, and evaluates HITL requirements before dispatch.
    This serves as a unified terminal node for custom workflows.
    """
    def __init__(self, toolbox: Toolbox, memory: MemoryService, config: dict):
        self.toolbox = toolbox
        self.memory = memory
        self.config = config
        
    async def __call__(self, state: GraphState) -> dict[str, Any]:
        prospect_id = state.get("prospect_id")
        from core.pubsub import pubsub_broker
        await pubsub_broker.publish(prospect_id, {
            "type": "AgentExecution",
            "agent": "ender_node",
            "message": "Finalizing workflow, summarizing results and dispatching..."
        })
        
        # Summarize
        summary_prompt = f"""
        Summarize the findings for {state['data'].get('company_name')}.
        Available data:
        - Firmographics: {state['data'].get('firmographics', {})}
        - Tech Stack: {state['data'].get('tech_stack', {})}
        - Enriched Data: {state['data'].get('enriched_data', {})}
        - ICP Score: {state.get('icp_score')}
        - Validation Notes: {state.get('validation_notes', [])}
        - Draft Outreach: {state.get('draft_outreach')}
        
        Provide a concise, professional summary of the prospect's viability.
        """
        summary = await self.toolbox.generate_text(
            prompt=summary_prompt,
            fallback="Summary generation failed.",
            strategy="fast"
        )
        
        # Evaluate HITL
        overall_status = state.get("overall_status", "PENDING")
        confidence_score = state.get("confidence_score", 1.0)
        has_conflict = state.get("has_conflict", False)
        
        if confidence_score < 0.7 or has_conflict or overall_status == "REJECTED":
            overall_status = "HITL"
            await pubsub_broker.publish(prospect_id, {
                "type": "AgentExecution",
                "agent": "ender_node",
                "message": "Low confidence or conflict detected. Routing to HITL."
            })
        else:
            overall_status = "APPROVED"
            await pubsub_broker.publish(prospect_id, {
                "type": "AgentExecution",
                "agent": "ender_node",
                "message": "Prospect approved automatically. Sending webhook."
            })
            
        # Optional: in a real system we would send the webhook here
        
        return {
            "data": {"summary_object": summary},
            "overall_status": overall_status,
            "executed_agents": ["ender_node"]
        }
