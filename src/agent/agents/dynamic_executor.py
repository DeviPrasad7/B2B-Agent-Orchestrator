import json
from typing import Any
from ..base import AgentNode
from ..state import GraphState
from core.logging import logger
from .registry import register_agent
from models.database import async_session, CustomAgent
from sqlalchemy import select

@register_agent("dynamic_agent_executor", "Generic node that executes dynamically generated Custom Agents based on next_custom_agent state.")
class DynamicAgentExecutorNode(AgentNode):
    async def __call__(self, state: GraphState) -> dict[str, Any]:
        target_agent_name = state.get("next_custom_agent")
        if not target_agent_name:
            return {"executed_agents": ["dynamic_agent_executor"]}
            
        prospect_id = state.get("prospect_id")
        
        async with async_session() as session:
            result = await session.execute(select(CustomAgent).where(CustomAgent.name == target_agent_name))
            agent_def = result.scalars().first()
            
        if not agent_def:
            logger.error(f"DynamicAgentExecutor: Custom agent '{target_agent_name}' not found.", prospect_id=prospect_id)
            return {"executed_agents": ["dynamic_agent_executor"]}
            
        logger.info(f"Executing Custom Agent: {target_agent_name}", prospect_id=prospect_id)
            
        prompt = f"""
{agent_def.system_prompt}
        
Current Gathered Data: {json.dumps(state.get("data", {}))}
"""
        
        # Basic implementation: just use LLM to process the prompt based on gathered data
        response = await self.toolbox.generate_text(prompt=prompt)
        
        data = state.get("data", {})
        data[f"{target_agent_name}_output"] = response
        
        return {
            "data": data,
            "executed_agents": ["dynamic_agent_executor"]
        }
