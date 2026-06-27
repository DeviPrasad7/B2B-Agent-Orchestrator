from functools import partial
from typing import Literal
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg_pool import AsyncConnectionPool

from core.settings import settings

from .state import GraphState
from .agents import (
    planner_node,
    monitor_node,
    score_node,
    hitl_gateway_node,
    tech_stack_detector_node,
    enricher_node,
    competitor_intel_node,
    cross_validator_node,
    summarizer_node,
    output_dispatcher_node,
    persona_matcher_node,
    contact_finder_node
)

def setup_graph(toolbox, memory_service):
    # Initialize graph
    workflow = StateGraph(GraphState)

    # Add all nodes with injected dependencies
    workflow.add_node("planner_node", partial(planner_node, toolbox=toolbox, memory=memory_service))
    workflow.add_node("monitor_node", partial(monitor_node, toolbox=toolbox, memory=memory_service))
    workflow.add_node("score_node", partial(score_node, toolbox=toolbox, memory=memory_service))
    workflow.add_node("hitl_gateway_node", partial(hitl_gateway_node, toolbox=toolbox, memory=memory_service))
    workflow.add_node("tech_stack_detector_node", partial(tech_stack_detector_node, toolbox=toolbox, memory=memory_service))
    workflow.add_node("enricher_node", partial(enricher_node, toolbox=toolbox, memory=memory_service))
    workflow.add_node("competitor_intel_node", partial(competitor_intel_node, toolbox=toolbox, memory=memory_service))
    workflow.add_node("cross_validator_node", partial(cross_validator_node, toolbox=toolbox, memory=memory_service))
    workflow.add_node("persona_matcher_node", partial(persona_matcher_node, toolbox=toolbox, memory=memory_service))
    workflow.add_node("contact_finder_node", partial(contact_finder_node, toolbox=toolbox, memory=memory_service))
    workflow.add_node("summarizer_node", partial(summarizer_node, toolbox=toolbox, memory=memory_service))
    workflow.add_node("output_dispatcher_node", partial(output_dispatcher_node, toolbox=toolbox, memory=memory_service))

    # All paths start at the planner
    workflow.add_edge(START, "planner_node")
    
    # The planner decides where to go next based on state["next_node"]
    def route_from_planner(state: GraphState) -> str:
        return state.get("next_node", "__end__")
        
    workflow.add_conditional_edges(
        "planner_node",
        route_from_planner,
        {
            "monitor_node": "monitor_node",
            "score_node": "score_node",
            "tech_stack_detector_node": "tech_stack_detector_node",
            "enricher_node": "enricher_node",
            "competitor_intel_node": "competitor_intel_node",
            "cross_validator_node": "cross_validator_node",
            "persona_matcher_node": "persona_matcher_node",
            "contact_finder_node": "contact_finder_node",
            "summarizer_node": "summarizer_node",
            "hitl_gateway_node": "hitl_gateway_node",
            "output_dispatcher_node": "output_dispatcher_node",
            "__end__": END
        }
    )
    
    # All worker nodes return to the planner so it can decide the next step
    workflow.add_edge("monitor_node", "planner_node")
    workflow.add_edge("score_node", "planner_node")
    workflow.add_edge("tech_stack_detector_node", "planner_node")
    workflow.add_edge("enricher_node", "planner_node")
    workflow.add_edge("competitor_intel_node", "planner_node")
    workflow.add_edge("cross_validator_node", "planner_node")
    workflow.add_edge("persona_matcher_node", "planner_node")
    workflow.add_edge("contact_finder_node", "planner_node")
    workflow.add_edge("summarizer_node", "planner_node")
    workflow.add_edge("hitl_gateway_node", "planner_node")
    workflow.add_edge("output_dispatcher_node", END) # dispatcher always ends

    return workflow

async def get_app(toolbox, memory_service):
    workflow = setup_graph(toolbox, memory_service)
    
    # PostgreSQL-backed checkpointer for durable HITL state
    connection_string = settings.get_checkpoint_db_url()
    pool = AsyncConnectionPool(
        conninfo=connection_string,
        max_size=5,
        open=False,            # opened explicitly below
    )
    await pool.open()

    checkpointer = AsyncPostgresSaver(pool)
    # Create checkpoint tables if they don't exist (idempotent)
    await checkpointer.setup()

    # Compile the workflow - NO interrupt_before since we use inline interrupt()
    app = workflow.compile(
        checkpointer=checkpointer
    )
    return app
