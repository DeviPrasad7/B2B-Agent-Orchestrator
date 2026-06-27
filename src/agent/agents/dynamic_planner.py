"""
Dynamic Planner node.

This node orchestrates the graph by deciding which node to execute next.
It uses the LLM to inspect the current state and the available agents, and outputs a JSON response with the `next_node`.
"""

import json
from typing import Any
from core.logging import logger

from ..state import GraphState
from ..utils import Toolbox
from services.memory_service import MemoryService
from ..base import AgentNode

class DynamicPlannerNode(AgentNode):
    def __init__(self, toolbox: Toolbox, memory: MemoryService, config: dict, registry: Any):
        self.toolbox = toolbox
        self.memory = memory
        self.config = config
        self.registry = registry
        
    async def __call__(self, state: GraphState) -> dict[str, Any]:
        prospect_id = state.get("prospect_id", "unknown")
        executed = set(state.get("executed_agents", []))
        last_agent = state.get("last_agent")
        simulate_failure = state.get("simulate_failure", False)
        retry_counts = state.get("retry_counts", {})
        overall_status = state.get("overall_status", "PENDING")
        
        if overall_status in ["NO_ACTION", "REJECTED", "TIMEOUT", "COMPLETED"]:
            return {"next_node": "__end__"}
            
        if overall_status == "APPROVED":
            return {"executed_agents": ["dynamic_planner_node"], "next_node": "output_dispatcher_node"}
        
        # 1. Simulate Failure Toggle (Bonus Demo Feature)
        if simulate_failure and last_agent and retry_counts.get(last_agent, 0) < 2:
            logger.warning(
                "DynamicPlanner: Simulating failure, forcing retry",
                prospect_id=prospect_id,
                agent=last_agent,
                retry_count=retry_counts.get(last_agent, 0) + 1
            )
            current_retries = retry_counts.get(last_agent, 0)
            return {
                "executed_agents": ["dynamic_planner_node"],
                "next_node": last_agent,
                "retry_counts": {last_agent: current_retries + 1}
            }
            
        # 2. Prepare context for the LLM
        agents = self.registry.list_agents_with_descriptions()
        
        custom_agent_names = []
        try:
            from models.database import async_session, CustomAgent
            from sqlalchemy import select
            async with async_session() as session:
                result = await session.execute(select(CustomAgent))
                custom_agents = result.scalars().all()
                for ca in custom_agents:
                    agents.append({"name": ca.name, "description": ca.description, "is_custom": True})
                    custom_agent_names.append(ca.name)
        except Exception as e:
            logger.error("Failed to fetch custom agents", error=str(e))
            
        # Exclude already executed agents
        available_agents = [a for a in agents if a["name"] not in executed and a["name"] != "dynamic_agent_executor"]
        
        if not available_agents:
            logger.info("DynamicPlanner: No more available agents, ending workflow.", prospect_id=prospect_id)
            return {"executed_agents": ["dynamic_planner_node"], "next_node": "__end__"}
            
        prompt = f"""
You are the dynamic planner orchestrating a B2B sales prospect enrichment workflow.

Current State:
- Prospect ID: {prospect_id}
- Company Name: {state.get("data", {}).get("company_name")}
- Overall Status: {overall_status}
- Executed Agents: {list(executed)}
- Data gathered so far: {json.dumps(state.get("data", {}), default=str)}

Available Agents:
{json.dumps(available_agents, indent=2)}

Rules:
- Choose the single best next agent from the Available Agents list to execute next.
- If we have all required firmographic and tech stack data, proceed to 'cross_validator_node', then 'persona_matcher_node', then 'contact_finder_node'.
- If we have all data, choose 'summarizer_node'.
- If 'summarizer_node' is executed, choose 'hitl_gateway_node'.
- If 'hitl_gateway_node' is executed, choose 'output_dispatcher_node'.
- Reply ONLY with a JSON object.

Output format:
{{
    "reasoning": "Brief explanation of why this agent was chosen based on missing data or next logical step.",
    "next_node": "agent_name_here"
}}
"""
        
        # 3. Call LLM
        try:
            llm_response = await self.toolbox.generate_text(
                prompt=prompt,
                fallback='{"next_node": "fallback", "reasoning": "fallback"}',
                require_json=True
            )
            
            # Clean response of markdown backticks
            clean_response = llm_response.strip()
            if clean_response.startswith('```json'):
                clean_response = clean_response[7:]
            elif clean_response.startswith('```'):
                clean_response = clean_response[3:]
            if clean_response.endswith('```'):
                clean_response = clean_response[:-3]
            clean_response = clean_response.strip()
            
            parsed = json.loads(clean_response)
            next_node = parsed.get("next_node")
            
            # Validate against registry
            valid_nodes = [a["name"] for a in agents] + ["__end__"]
            if next_node not in valid_nodes:
                raise ValueError(f"LLM suggested invalid node: {next_node}")
                
            logger.info(
                "DynamicPlanner: LLM selected next node",
                prospect_id=prospect_id,
                next_node=next_node,
                reasoning=parsed.get("reasoning")
            )
            
            if next_node in custom_agent_names:
                return {
                    "executed_agents": ["dynamic_planner_node", next_node],
                    "next_node": "dynamic_agent_executor",
                    "next_custom_agent": next_node
                }
            
            return {
                "executed_agents": ["dynamic_planner_node"],
                "next_node": next_node,
            }
            
        except Exception as e:
            logger.warning(
                "DynamicPlanner: LLM failed or returned invalid output, falling back to deterministic sequence",
                error=str(e),
                prospect_id=prospect_id
            )
            # 4. Fallback: deterministic linear sequence based on executed_agents
            sequence = [a["name"] for a in agents]
            
            for node in sequence:
                if node not in executed:
                    return {"executed_agents": ["dynamic_planner_node"], "next_node": node}
            
            return {"executed_agents": ["dynamic_planner_node"], "next_node": "__end__"}
