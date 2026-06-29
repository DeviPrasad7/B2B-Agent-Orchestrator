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
                "retry_counts": {last_agent: current_retries + 1},
                "recent_thoughts": [f"Simulating failure, forcing retry on {last_agent}"]
            }
            
        # 2. Custom Workflow Enforcement (DAG Routing)
        custom_workflow_steps = state.get("custom_workflow_steps")
        if custom_workflow_steps:
            if isinstance(custom_workflow_steps, dict) and "nodes" in custom_workflow_steps:
                nodes = custom_workflow_steps.get("nodes", [])
                edges = custom_workflow_steps.get("edges", [])
                
                dispatched = set(state.get("dispatched_agents", []))
                
                # Fetch custom agent names to handle dynamic_agent_executor routing
                custom_agent_names = []
                try:
                    from models.database import async_session, CustomAgent
                    from sqlalchemy import select
                    async with async_session() as session:
                        result = await session.execute(select(CustomAgent))
                        custom_agents = result.scalars().all()
                        custom_agent_names = [ca.name for ca in custom_agents]
                except Exception as e:
                    logger.error("Failed to fetch custom agents", error=str(e))
                
                def are_dependencies_met(node_id: str) -> bool:
                    incoming_edges = [e for e in edges if e.get("target") == node_id]
                    for edge in incoming_edges:
                        source_id = edge.get("source")
                        source_node = next((n for n in nodes if n.get("id") == source_id), None)
                        if not source_node:
                            continue
                        agent_name = source_node.get("data", {}).get("agentId")
                        if agent_name not in executed:
                            return False
                    return True
                    
                next_agents_to_run = []
                new_dispatched = []
                
                for node in nodes:
                    node_id = node.get("id")
                    agent_name = node.get("data", {}).get("agentId")
                    
                    if not agent_name or agent_name in executed or agent_name in dispatched:
                        continue
                        
                    if are_dependencies_met(node_id):
                        next_agents_to_run.append(agent_name)
                        new_dispatched.append(agent_name)
                
                if not next_agents_to_run:
                    # If everything is executed, we are done. Note: len(nodes) might include empty nodes, so count valid agents
                    valid_agents_count = len([n for n in nodes if n.get("data", {}).get("agentId")])
                    if len(executed) >= valid_agents_count:
                        logger.info("DynamicPlanner: Custom workflow complete.", prospect_id=prospect_id)
                        return {"executed_agents": ["dynamic_planner_node"], "next_node": "__end__"}
                    else:
                        logger.info("DynamicPlanner: Waiting for pending agents...", prospect_id=prospect_id)
                        return {"executed_agents": ["dynamic_planner_node"], "next_node": []}
                        
                logger.info(f"DynamicPlanner: Dispatching parallel nodes: {next_agents_to_run}", prospect_id=prospect_id)
                
                dispatch_nodes = []
                next_ca = None
                for ag in next_agents_to_run:
                    if ag in custom_agent_names:
                        if next_ca is None:
                            next_ca = ag
                            dispatch_nodes.append("dynamic_agent_executor")
                        else:
                            # Only run one custom agent at a time in parallel to avoid next_custom_agent race condition
                            new_dispatched.remove(ag)
                    else:
                        dispatch_nodes.append(ag)
                        
                return {
                    "executed_agents": ["dynamic_planner_node"],
                    "dispatched_agents": new_dispatched,
                    "next_node": dispatch_nodes,
                    "next_custom_agent": next_ca if next_ca else state.get("next_custom_agent"),
                    "recent_thoughts": [f"Dispatching parallel: {dispatch_nodes}"]
                }
            else:
                # Fallback for old linear custom workflows
                next_step = None
                for step in custom_workflow_steps:
                    if step not in executed:
                        next_step = step
                        break
                        
                if not next_step:
                    return {"executed_agents": ["dynamic_planner_node"], "next_node": "__end__"}
                    
                custom_agent_names = []
                try:
                    from models.database import async_session, CustomAgent
                    from sqlalchemy import select
                    async with async_session() as session:
                        result = await session.execute(select(CustomAgent))
                        custom_agent_names = [ca.name for ca in result.scalars().all()]
                except Exception as e:
                    pass
                    
                if next_step in custom_agent_names:
                    return {
                        "executed_agents": ["dynamic_planner_node", next_step],
                        "next_node": "dynamic_agent_executor",
                        "next_custom_agent": next_step,
                        "recent_thoughts": [f"Routing to custom agent {next_step}"]
                    }
                return {
                    "executed_agents": ["dynamic_planner_node"],
                    "next_node": next_step,
                    "recent_thoughts": [f"Routing to {next_step}"]
                }

        # 3. Prepare context for the LLM
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
        available_agents = []
        for a in agents:
            if a["name"] not in executed and a["name"] != "dynamic_agent_executor":
                # Truncate description to save tokens
                desc = a.get("description", "")
                if len(desc) > 80:
                    desc = desc[:77] + "..."
                available_agents.append({"name": a["name"], "desc": desc})
        
        if not available_agents:
            logger.info("DynamicPlanner: No more available agents, ending workflow.", prospect_id=prospect_id)
            return {"executed_agents": ["dynamic_planner_node"], "next_node": "__end__"}
            
        # Intelligently truncate context data to preserve semantic meaning while saving thousands of tokens
        def truncate_data(d: Any, max_len: int = 150) -> Any:
            if isinstance(d, dict):
                return {k: truncate_data(v, max_len) for k, v in d.items()}
            elif isinstance(d, list):
                return [truncate_data(v, max_len) for v in d[:3]] # Keep max 3 items
            elif isinstance(d, str):
                return d if len(d) <= max_len else d[:max_len] + "..."
            return d
            
        context_data = truncate_data(state.get("data", {}))
        
        prompt = f"""
You are a B2B sales workflow planner.
Status: {overall_status}
Executed: {list(executed)}
Data Gathered: {json.dumps(context_data, default=str)}

Agents:
{json.dumps(available_agents)}

- Rules:
- Choose the best next agent based on missing data.
- **CRITICAL**: If a custom agent exists in the available agents list (i.e. agents dynamically added by the user), you MUST heavily consider using it to gather specialized data before proceeding to validation or summarization.
- Once firmographic & tech stack data exist, do 'cross_validator_node' -> 'persona_matcher_node' -> 'contact_finder_node'.
- Once contacts are found, choose 'outreach_generator_node'.
- Once all data is gathered and outreach is drafted, choose 'summarizer_node'.
- After 'summarizer_node', choose 'hitl_gateway_node'.
- After 'hitl_gateway_node', choose 'output_dispatcher_node'.
- Return ONLY JSON.

Format:
{{"reasoning":"Brief reason","next_node":"agent_name"}}
"""
        
        # 3. Call LLM
        try:
            llm_response = await self.toolbox.generate_text(
                prompt=prompt,
                fallback='{"next_node": "fallback", "reasoning": "fallback"}',
                require_json=True,
                strategy="fast"
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
            
            # Remove trailing commas common in LLM outputs before parsing
            import re
            clean_response = re.sub(r',\s*}', '}', clean_response)
            clean_response = re.sub(r',\s*\]', ']', clean_response)
            
            parsed = json.loads(clean_response)
            next_node = parsed.get("next_node")
            
            # Validate against registry and available (unexecuted) agents
            valid_nodes = [a["name"] for a in available_agents] + ["__end__"]
            if next_node not in valid_nodes:
                raise ValueError(f"LLM suggested invalid or already executed node: {next_node}")
                
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
                    "next_custom_agent": next_node,
                    "recent_thoughts": [parsed.get("reasoning", "Routing to custom agent")]
                }
            
            return {
                "executed_agents": ["dynamic_planner_node"],
                "next_node": next_node,
                "recent_thoughts": [parsed.get("reasoning", f"Routing to {next_node}")]
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
                    if node in custom_agent_names:
                        return {
                            "executed_agents": ["dynamic_planner_node", node],
                            "next_node": "dynamic_agent_executor",
                            "next_custom_agent": node,
                            "recent_thoughts": [f"Fallback: Routing to custom agent {node}"]
                        }
                    return {"executed_agents": ["dynamic_planner_node"], "next_node": node, "recent_thoughts": [f"Fallback: Routing to {node}"]}
            
            return {"executed_agents": ["dynamic_planner_node"], "next_node": "__end__", "recent_thoughts": ["Fallback: Pipeline complete"]}
