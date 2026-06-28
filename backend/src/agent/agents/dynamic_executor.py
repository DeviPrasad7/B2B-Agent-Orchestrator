"""
DynamicAgentExecutorNode – generic executor for user-defined Custom Agents.

Fetches the agent definition from the DB, builds a prompt using the agent's
system_prompt and the current state, then calls the LLM and stores the output
under ``data[<agent_name>_output]``.
"""
import json
from typing import Any

from ..base import AgentNode
from ..registry import register_agent   # ✅ correct relative import (parent package)
from ..state import GraphState
from ..utils import Toolbox
from services.memory_service import MemoryService
from core.logging import logger


@register_agent(
    "dynamic_agent_executor",
    description="Generic node that executes user-created Custom Agents based on next_custom_agent state.",
)
class DynamicAgentExecutorNode(AgentNode):
    """Executes dynamically registered Custom Agents loaded from the database."""

    def __init__(self, toolbox: Toolbox, memory: MemoryService, config: dict) -> None:
        self.toolbox = toolbox
        self.memory = memory
        self.config = config

    async def __call__(self, state: GraphState) -> dict[str, Any]:
        target_agent_name = state.get("next_custom_agent")
        if not target_agent_name:
            return {"executed_agents": ["dynamic_agent_executor"]}

        prospect_id = state.get("prospect_id", "unknown")

        from models.database import async_session, CustomAgent
        from sqlalchemy import select

        async with async_session() as session:
            result = await session.execute(
                select(CustomAgent).where(CustomAgent.name == target_agent_name)
            )
            agent_def = result.scalars().first()

        if not agent_def:
            logger.error(
                "DynamicAgentExecutor: Custom agent not found",
                agent_name=target_agent_name,
                prospect_id=prospect_id,
            )
            return {"executed_agents": ["dynamic_agent_executor"]}

        logger.info(
            "Executing Custom Agent",
            agent_name=target_agent_name,
            prospect_id=prospect_id,
        )

        fallback = json.dumps({"output": "Custom agent produced no output."})

        try:
            from langgraph.prebuilt import create_react_agent
            from ..tools import get_agent_tools

            llm = self.toolbox.get_llm(strategy="heavy")
            available_tools_dict = get_agent_tools(self.toolbox, agent_id=str(agent_def.id))
            
            allowed_keys = [t.strip() for t in agent_def.allowed_tools] if agent_def.allowed_tools else []
            active_tools = [available_tools_dict[k] for k in allowed_keys if k in available_tools_dict]

            if active_tools:
                react_agent = create_react_agent(llm, tools=active_tools, state_modifier=agent_def.system_prompt)
                user_msg = f"Task: Execute your instructions based on the data.\nCurrent Gathered Data: {json.dumps(state.get('data', {}), default=str)}"
                result = await react_agent.ainvoke({"messages": [("user", user_msg)]})
                response = result["messages"][-1].content
            else:
                # Fallback to simple generation if no tools
                prompt = (
                    f"{agent_def.system_prompt}\n\n"
                    f"Current Gathered Data: {json.dumps(state.get('data', {}), default=str)}"
                )
                response = await self.toolbox.generate_text(
                    prompt=prompt,
                    fallback=fallback,
                )
        except Exception as exc:
            logger.error("DynamicAgentExecutor: Agent execution failed", error=str(exc))
            response = fallback

        # Return delta only – do NOT mutate/spread the full state dict
        return {
            "data": {f"{target_agent_name}_output": response},
            "executed_agents": ["dynamic_agent_executor", target_agent_name],
        }
