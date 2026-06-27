import json
import re
from typing import Any
from ..state import GraphState
from ..utils import Toolbox
from services.memory_service import MemoryService
from core.logging import logger
from ..base import AgentNode
from ..registry import AgentRegistry

class PlannerNode(AgentNode):
    def __init__(self, toolbox: Toolbox, memory: MemoryService, config: dict, registry: AgentRegistry):
        self.toolbox = toolbox
        self.memory = memory
        self.config = config
        self.registry = registry

    def _deterministic_fallback(self, state: dict) -> str:
        data = state.get("data", {})
        executed = state.get("executed_agents", [])
        
        has_company = bool(data.get('company_name'))
        has_scored = bool(data.get('scored_signals'))
        has_enriched = bool(data.get('firmographics'))
        has_tech = 'tech_stack_detector_node' in executed
        has_validated = 'cross_validator_node' in executed
        has_personas = bool(data.get('personas'))
        has_contacts = bool(data.get('contacts'))
        has_summary = bool(data.get('summary_object'))
        
        if not has_scored:
            return "score_node"
        elif not has_enriched:
            return "enricher_node"
        elif not has_tech:
            return "tech_stack_detector_node"
        elif not has_validated:
            return "cross_validator_node"
        elif not has_personas:
            return "persona_matcher_node"
        elif not has_contacts:
            return "contact_finder_node"
        elif not has_summary:
            return "summarizer_node"
        else:
            return "hitl_gateway_node"

    async def __call__(self, state: GraphState) -> dict[str, Any]:
        prospect_id = state.get("prospect_id", "unknown")
        executed_agents = state.get("executed_agents", [])
        overall_status = state.get("overall_status", "PENDING")
        errors = state.get("errors", [])
        retry_counts = state.get("retry_counts", {})
        
        logger.info(f"Planner evaluating next step", extra={"prospect_id": prospect_id, "state": overall_status})
        
        if overall_status in ["NO_ACTION", "REJECTED", "TIMEOUT", "COMPLETED"]:
            return {"next_node": "__end__"}
            
        if overall_status == "APPROVED":
            return {"executed_agents": ["planner_node"], "next_node": "output_dispatcher_node"}
            
        # Error handling & retries
        if executed_agents:
            last_agent = executed_agents[-1]
            if last_agent != "planner_node" and errors:
                # Did the last agent raise an error?
                if any(e.startswith(last_agent) for e in errors[-1:]):
                    max_retries = self.config.get("MAX_RETRIES", 3)
                    current_retries = retry_counts.get(last_agent, 0)
                    if current_retries < max_retries:
                        logger.warning(f"Retrying agent {last_agent}", extra={"attempt": current_retries + 1, "prospect_id": prospect_id})
                        return {
                            "executed_agents": ["planner_node"],
                            "next_node": last_agent,
                            "retry_counts": {last_agent: current_retries + 1}
                        }
                    else:
                        logger.error(f"Max retries reached for {last_agent}, skipping", extra={"prospect_id": prospect_id})
            
        available_agents = self.registry.list_agents()
        agent_descriptions = []
        for name in available_agents:
            desc = self.registry.get_description(name)
            agent_descriptions.append(f"- {name}: {desc}")
            
        agents_str = "\n".join(agent_descriptions)
        
        prompt = f"""
You are the Planner Agent for a B2B SaaS Customer Discovery pipeline.
Your job is to decide the next agent to execute based on the current state.

Available Agents:
{agents_str}

Current State Summary:
- Executed Agents: {executed_agents}
- Overall Status: {overall_status}
- Has Company Name: {bool(state.get('data', {}).get('company_name'))}
- Has Summary: {bool(state.get('data', {}).get('summary_object'))}
- Has Firmographics: {bool(state.get('data', {}).get('firmographics'))}
- Recent Errors: {errors[-2:] if errors else 'None'}
- Retry Counts: {retry_counts}

Output ONLY a structured JSON object with the following keys:
1. "next_node": The exact name of the next agent to run. If the workflow is complete, output "__end__".
2. "reasoning": A brief explanation of why this agent was chosen.
3. "params": (Optional) Any specific parameters to pass.
"""
        
        fallback_json = '{"next_node": "__end__", "reasoning": "Fallback"}'
        
        try:
            response = await self.toolbox.generate_text(prompt, fallback_json, require_json=True)
            
            # Clean response of any markdown backticks that the LLM might have returned despite instructions
            clean_response = response.strip()
            if clean_response.startswith('```json'):
                clean_response = clean_response[7:]
            elif clean_response.startswith('```'):
                clean_response = clean_response[3:]
            if clean_response.endswith('```'):
                clean_response = clean_response[:-3]
            clean_response = clean_response.strip()
            
            try:
                data = json.loads(clean_response)
                next_node = data.get("next_node", "__end__")
                logger.info("LLM Planner decision", extra={"decision": data, "prospect_id": prospect_id})
            except json.JSONDecodeError:
                logger.warning("LLM Planner returned invalid JSON, using fallback", extra={"response": response})
                next_node = self._deterministic_fallback(state)
                
            if next_node not in available_agents and next_node != "__end__":
                next_node = self._deterministic_fallback(state)
                
            return {"executed_agents": ["planner_node"], "next_node": next_node}
            
        except Exception as e:
            logger.error(f"Planner LLM failed: {str(e)}", extra={"prospect_id": prospect_id})
            next_node = self._deterministic_fallback(state)
            return {"executed_agents": ["planner_node"], "next_node": next_node}
