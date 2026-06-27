import time
from typing import Any
from ..state import GraphState
from ..utils import Toolbox, MonitoringService
from services.memory_service import MemoryService
from ..base import AgentNode
from ..registry import register_agent

@register_agent("score_node", description="Scores the company against ICP criteria")
class ScoreNode(AgentNode):
    def __init__(self, toolbox: Toolbox, memory: MemoryService, config: dict):
        self.toolbox = toolbox
        self.memory = memory
        self.config = config

    async def __call__(self, state: GraphState) -> dict[str, Any]:
        prospect_id = state.get("prospect_id", "unknown")
        try:
            signals = state.get("data", {}).get("raw_signals", [])

            # Prefer fresh per-workflow ICP config from state; fall back to startup snapshot.
            icp = state.get("config", {}).get("icp", {})
            if not icp:
                icp = self.config.get("icp", {})

            keywords = []
            if isinstance(icp, dict):
                for key in ["industries", "tech_stack", "behaviors", "locations"]:
                    keywords.extend([str(x).lower() for x in icp.get(key, []) if x])

            scored = []
            for s in signals:
                signal_lower = str(s).lower()
                matches = sum(1 for kw in keywords if kw in signal_lower)
                score = min(100.0, (matches / max(len(keywords), 1)) * 100.0)
                scored.append({"signal": s, "score": score})

            scored = sorted(scored, key=lambda x: x["score"], reverse=True)[:20]

            if not scored:
                # No signals yet (e.g. manually submitted prospect before enrichment).
                # Do NOT terminate — let the pipeline continue; confidence stays 0 so
                # the HITL gateway will catch it.
                MonitoringService.log_info(prospect_id, "No signals to score; continuing pipeline with 0 confidence")
                return {
                    "executed_agents": ["score_node"],
                    "data": {"scored_signals": []},
                    "confidence_score": 0.0,
                }

            avg_score = sum(x["score"] for x in scored) / len(scored)
            confidence_score = avg_score / 100.0

            return {
                "executed_agents": ["score_node"],
                "data": {"scored_signals": scored},
                "confidence_score": confidence_score,
            }
        except Exception as e:
            MonitoringService.log_error(prospect_id, f"SCORE_ERROR: {str(e)}")
            return {
                "executed_agents": ["score_node"],
                "errors": [f"score_node: {str(e)}"],
                "data": {"scored_signals": []},
            }

