from functools import partial
from typing import Literal
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg_pool import AsyncConnectionPool

from core.settings import settings

from .state import GraphState
from .registry import registry
from .agents.planner import PlannerNode

# Ensure all agents are registered by importing the agents package
import agent.agents

def setup_graph(toolbox, memory_service, config: dict):
    # Initialize graph
    workflow = StateGraph(GraphState)

    # Instantiate and add the planner node manually
    planner_instance = PlannerNode(toolbox, memory_service, config, registry)
    workflow.add_node("planner_node", planner_instance)

    # Add all registered nodes dynamically
    for name in registry.list_agents():
        agent_cls = registry.get_agent(name)
        agent_instance = agent_cls(toolbox, memory_service, config)
        workflow.add_node(name, agent_instance)

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
    for name in registry.list_agents():
        if name == "output_dispatcher_node":
            workflow.add_edge(name, END) # dispatcher always ends
        else:
            workflow.add_edge(name, "planner_node")

    return workflow

async def get_app(toolbox, memory_service, config: dict):
    workflow = setup_graph(toolbox, memory_service, config)
    
    # PostgreSQL-backed checkpointer for durable HITL state
    connection_string = settings.get_checkpoint_db_url()
    
    # Run setup with an autocommit connection to allow CREATE INDEX CONCURRENTLY
    import psycopg
    async with await psycopg.AsyncConnection.connect(connection_string, autocommit=True) as setup_conn:
        setup_checkpointer = AsyncPostgresSaver(setup_conn)
        await setup_checkpointer.setup()

    pool = AsyncConnectionPool(
        conninfo=connection_string,
        max_size=5,
        open=False,            # opened explicitly below
    )
    await pool.open()

    checkpointer = AsyncPostgresSaver(pool)

    # Compile the workflow - NO interrupt_before since we use inline interrupt()
    app = workflow.compile(
        checkpointer=checkpointer
    )
    return app
