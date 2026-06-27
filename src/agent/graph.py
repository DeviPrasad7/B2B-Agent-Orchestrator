from typing import Literal
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from agent.state import GraphState
from agent.nodes import (
    monitor_node,
    score_node,
    hitl_gateway_node,
    tech_stack_detector_node,
    enricher_node,
    competitor_intel_node,
    cross_validator_node,
    summarizer_node,
    output_dispatcher_node,
    consolidation_node,
    persona_matcher_node,
    contact_finder_node
)

def route_post_scoring(state: GraphState) -> Literal["__end__", "parallel_enrichment_start"]:
    if state.get("overall_status") == "NO_ACTION":
        return "__end__"
    return "parallel_enrichment_start"

def route_post_enrichment(state: GraphState) -> Literal["competitor_intel_node", "cross_validator_node"]:
    tech_stack = state.get("data", {}).get("tech_stack", [])
    if tech_stack:
        return "competitor_intel_node"
    return "cross_validator_node"

def route_post_validation(state: GraphState) -> Literal["hitl_gateway_node", "persona_matcher_node", "summarizer_node"]:
    confidence = state.get("confidence_score", 100.0)
    conflict = state.get("has_conflict", False)
    if confidence < 40.0 or conflict:
        return "hitl_gateway_node"
        
    company_name = state.get("data", {}).get("company_name")
    if company_name:
        return "persona_matcher_node"
        
    return "summarizer_node"
    
def route_post_hitl(state: GraphState) -> Literal["output_dispatcher_node", "__end__"]:
    status = state.get("overall_status")
    if status in ["APPROVED", "EDITED"]:
        return "output_dispatcher_node"
    return "__end__"

# Initialize graph
workflow = StateGraph(GraphState)

# Add nodes
workflow.add_node("monitor_node", monitor_node)
workflow.add_node("score_node", score_node)
workflow.add_node("post_monitor_consolidation", consolidation_node)
workflow.add_node("hitl_gateway_node", hitl_gateway_node)

workflow.add_node("tech_stack_detector_node", tech_stack_detector_node)
workflow.add_node("enricher_node", enricher_node)
workflow.add_node("post_enrichment_consolidation", consolidation_node)

workflow.add_node("competitor_intel_node", competitor_intel_node)
workflow.add_node("cross_validator_node", cross_validator_node)
workflow.add_node("persona_matcher_node", persona_matcher_node)
workflow.add_node("contact_finder_node", contact_finder_node)
workflow.add_node("summarizer_node", summarizer_node)
workflow.add_node("output_dispatcher_node", output_dispatcher_node)

# ==============================================================================
# Graph Routing & Wiring
# ==============================================================================

# Phase 2: Monitoring & Scoring run in parallel (Wait, brief says "After monitor and score", implies monitor -> score -> branch. But graph currently has them in parallel. I'll stick to the scaffolding's parallel structure but route after consolidation.)
workflow.add_edge(START, "monitor_node")
workflow.add_edge(START, "score_node")

# Converge parallel branches
workflow.add_edge("monitor_node", "post_monitor_consolidation")
workflow.add_edge("score_node", "post_monitor_consolidation")

# Routing after initial phase
workflow.add_conditional_edges(
    "post_monitor_consolidation",
    route_post_scoring,
    {
        "__end__": END,
        "parallel_enrichment_start": "tech_stack_detector_node" 
    }
)
# Since parallel enrichment starts, we also need to route to enricher_node
workflow.add_edge("post_monitor_consolidation", "enricher_node")

# Converge Phase 4
workflow.add_edge("tech_stack_detector_node", "post_enrichment_consolidation")
workflow.add_edge("enricher_node", "post_enrichment_consolidation")

# Phase 5 & 6: Competitor Intel (Conditional) & Validation
workflow.add_conditional_edges(
    "post_enrichment_consolidation",
    route_post_enrichment,
    {
        "competitor_intel_node": "competitor_intel_node",
        "cross_validator_node": "cross_validator_node"
    }
)
workflow.add_edge("competitor_intel_node", "cross_validator_node")

# Phase 7: Confidence Check, Persona Matching & Summarization
workflow.add_conditional_edges(
    "cross_validator_node",
    route_post_validation,
    {
        "hitl_gateway_node": "hitl_gateway_node",
        "persona_matcher_node": "persona_matcher_node",
        "summarizer_node": "summarizer_node"
    }
)

workflow.add_edge("persona_matcher_node", "contact_finder_node")
workflow.add_edge("contact_finder_node", "summarizer_node")

# After summarization, ALWAYS route to HITL
workflow.add_edge("summarizer_node", "hitl_gateway_node")

# Phase 8: Final HITL Gateway before output
workflow.add_conditional_edges(
    "hitl_gateway_node",
    route_post_hitl,
    {
        "output_dispatcher_node": "output_dispatcher_node",
        "__end__": END
    }
)

workflow.add_edge("output_dispatcher_node", END)

from langgraph.checkpoint.sqlite import SqliteSaver
import sqlite3

# Memory Checkpointer using a separate database to avoid conflicts
conn = sqlite3.connect("checkpoints.db", check_same_thread=False)
memory = SqliteSaver(conn)

# Compile the workflow - NO interrupt_before since we use inline interrupt()
app = workflow.compile(
    checkpointer=memory
)
