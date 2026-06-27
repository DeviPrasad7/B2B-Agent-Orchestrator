from functools import partial
from typing import Literal
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.sqlite import SqliteSaver
import sqlite3

from .state import GraphState
from .agents import (
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

app = None

def setup_graph(toolbox, memory_store):
    global app
    
    # Initialize graph
    workflow = StateGraph(GraphState)

    # Add nodes with injected dependencies
    workflow.add_node("monitor_node", partial(monitor_node, toolbox=toolbox, memory=memory_store))
    workflow.add_node("score_node", partial(score_node, toolbox=toolbox, memory=memory_store))
    workflow.add_node("post_monitor_consolidation", partial(consolidation_node, toolbox=toolbox, memory=memory_store))
    workflow.add_node("hitl_gateway_node", partial(hitl_gateway_node, toolbox=toolbox, memory=memory_store))

    workflow.add_node("tech_stack_detector_node", partial(tech_stack_detector_node, toolbox=toolbox, memory=memory_store))
    workflow.add_node("enricher_node", partial(enricher_node, toolbox=toolbox, memory=memory_store))
    workflow.add_node("post_enrichment_consolidation", partial(consolidation_node, toolbox=toolbox, memory=memory_store))

    workflow.add_node("competitor_intel_node", partial(competitor_intel_node, toolbox=toolbox, memory=memory_store))
    workflow.add_node("cross_validator_node", partial(cross_validator_node, toolbox=toolbox, memory=memory_store))
    workflow.add_node("persona_matcher_node", partial(persona_matcher_node, toolbox=toolbox, memory=memory_store))
    workflow.add_node("contact_finder_node", partial(contact_finder_node, toolbox=toolbox, memory=memory_store))
    workflow.add_node("summarizer_node", partial(summarizer_node, toolbox=toolbox, memory=memory_store))
    workflow.add_node("output_dispatcher_node", partial(output_dispatcher_node, toolbox=toolbox, memory=memory_store))

    # ==============================================================================
    # Graph Routing & Wiring
    # ==============================================================================

    # Phase 2: Monitoring & Scoring run in parallel
    workflow.add_edge(START, "monitor_node")
    workflow.add_edge(START, "score_node")

    # Converge parallel branches
    workflow.add_edge("monitor_node", "post_monitor_consolidation")
    workflow.add_edge("score_node", "post_monitor_consolidation")

    def route_post_scoring(state: GraphState) -> Literal["__end__", "parallel_enrichment_start"]:
        if state.get("overall_status") == "NO_ACTION":
            return "__end__"
        return "parallel_enrichment_start"

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

    def route_post_enrichment(state: GraphState) -> Literal["competitor_intel_node", "cross_validator_node"]:
        tech_stack = state.get("data", {}).get("tech_stack", [])
        if tech_stack:
            return "competitor_intel_node"
        return "cross_validator_node"

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

    def route_post_validation(state: GraphState) -> Literal["hitl_gateway_node", "persona_matcher_node", "summarizer_node"]:
        confidence = state.get("confidence_score", 100.0)
        conflict = state.get("has_conflict", False)
        if confidence < 40.0 or conflict:
            return "hitl_gateway_node"
            
        company_name = state.get("data", {}).get("company_name")
        if company_name:
            return "persona_matcher_node"
            
        return "summarizer_node"

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

    def route_post_hitl(state: GraphState) -> Literal["output_dispatcher_node", "__end__"]:
        status = state.get("overall_status")
        if status in ["APPROVED", "EDITED"]:
            return "output_dispatcher_node"
        return "__end__"

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

    # Memory Checkpointer using a separate database to avoid conflicts
    conn = sqlite3.connect("checkpoints.db", check_same_thread=False)
    memory = SqliteSaver(conn)

    # Compile the workflow - NO interrupt_before since we use inline interrupt()
    app = workflow.compile(
        checkpointer=memory
    )
    return app
