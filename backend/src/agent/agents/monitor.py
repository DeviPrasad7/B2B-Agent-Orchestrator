"""
MonitorNode – fetches the company's website and builds raw signals for scoring.

If no website URL is present, returns a minimal placeholder signal so the
pipeline can continue to the enrichment stage.
"""
import time
from typing import Any

from ..base import AgentNode
from ..registry import register_agent
from ..state import GraphState
from ..utils import CircuitBreakerState, MonitoringService, Toolbox
from services.memory_service import MemoryService


@register_agent(
    "monitor_node",
    description="Fetches the company website and builds raw signals for ICP scoring",
)
class MonitorNode(AgentNode):
    def __init__(self, toolbox: Toolbox, memory: MemoryService, config: dict) -> None:
        self.toolbox = toolbox
        self.memory = memory
        self.config = config

    async def __call__(self, state: GraphState) -> dict[str, Any]:
        prospect_id = state.get("prospect_id", "unknown")
        try:
            cb_state = self.toolbox.circuit_breaker.check_health("RSS_SOURCE")
            if cb_state == CircuitBreakerState.OPEN:
                MonitoringService.log_warning(prospect_id, "Website source unavailable (circuit open), skipping")
                return {"executed_agents": ["monitor_node"]}

            website_url = state.get("data", {}).get("website_url")
            raw_signals = []

            if website_url:
                page = await self.toolbox.fetch_webpage(website_url, 10)
                # Extract meaningful signal from page content (first 500 chars of text)
                content_snippet = page.htmlContent[:500] if page.htmlContent else ""
                raw_signals.append({
                    "source": "website",
                    "timestamp": time.time(),
                    "content": content_snippet,
                    "url": website_url,
                })
            else:
                # No URL — add a minimal signal so subsequent agents can run
                company_name = state.get("data", {}).get("company_name", "")
                raw_signals.append({
                    "source": "manual",
                    "timestamp": time.time(),
                    "content": f"Manual submission: {company_name}",
                })

            event_hash = f"event_{prospect_id}"
            await self.memory.mark_event_processed(event_hash, prospect_id)
            self.toolbox.circuit_breaker.record_success("RSS_SOURCE")

            return {
                "executed_agents": ["monitor_node"],
                "data": {"raw_signals": raw_signals},
            }
        except Exception as e:
            self.toolbox.circuit_breaker.record_failure("RSS_SOURCE")
            MonitoringService.log_error(prospect_id, f"MONITOR_ERROR: {str(e)}")
            return {"executed_agents": ["monitor_node"], "errors": [f"monitor_node: {str(e)}"]}
