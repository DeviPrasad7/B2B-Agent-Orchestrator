from functools import partial
from typing import Literal
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from core.settings import settings

from .state import GraphState
from .base import SafeAgentWrapper
from .registry import registry
from .agents.dynamic_planner import DynamicPlannerNode

# Ensure all agents are registered by importing the agents package
import agent.agents

def setup_graph(toolbox, memory_service, config: dict):
    # Initialize graph
    workflow = StateGraph(GraphState)

    # Instantiate and add the dynamic planner node manually
    planner_instance = DynamicPlannerNode(toolbox, memory_service, config, registry)
    workflow.add_node("dynamic_planner", planner_instance)

    # Add all registered nodes dynamically
    for name in registry.list_agents():
        agent_cls = registry.get_agent(name)
        agent_instance = agent_cls(toolbox, memory_service, config)
        safe_agent = SafeAgentWrapper(agent_instance, name)
        workflow.add_node(name, safe_agent)

    # All paths start at the dynamic planner
    workflow.add_edge(START, "dynamic_planner")
    
    # The planner decides where to go next based on state["next_node"]
    def route_from_planner(state: GraphState) -> str | list[str]:
        return state.get("next_node", "__end__")

    # Build the path_map dynamically – adding a new @register_agent agent
    # automatically wires it into the graph without touching this file (OCP).
    path_map = {name: name for name in registry.list_agents()}
    path_map["__end__"] = END

    workflow.add_conditional_edges("dynamic_planner", route_from_planner, path_map)

    # All worker nodes return to the planner so it can decide the next step
    for name in registry.list_agents():
        if name == "output_dispatcher_node":
            workflow.add_edge(name, END)  # dispatcher always ends
        else:
            workflow.add_edge(name, "dynamic_planner")

    return workflow

async def get_app(toolbox, memory_service, config: dict):
    workflow = setup_graph(toolbox, memory_service, config)
    
    db_url = settings.get_checkpoint_db_url()
    
    if db_url.startswith("sqlite"):
        import aiosqlite
        from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
        db_path = db_url.split(":///", 1)[-1] if ":///" in db_url else ":memory:"
        pool = await aiosqlite.connect(db_path, uri=True)
        checkpointer = AsyncSqliteSaver(pool)
        await checkpointer.setup()
    else:
        import psycopg
        from psycopg_pool import AsyncConnectionPool
        from core.logging import logger
        # Run setup with an autocommit connection to allow CREATE INDEX CONCURRENTLY
        async with await psycopg.AsyncConnection.connect(db_url, autocommit=True) as setup_conn:
            setup_checkpointer = AsyncPostgresSaver(setup_conn)
            try:
                await setup_checkpointer.setup()
            except Exception as e:
                # Concurrent index creation can throw errors if multiple workers start. 
                # With WORKERS=1 this is rare, but we catch it just in case.
                logger.warning("Checkpointer setup failed (likely due to concurrent index creation)", error=str(e))

        pool = AsyncConnectionPool(
            conninfo=db_url,
            max_size=5,
            open=False,
        )
        await pool.open()
        checkpointer = AsyncPostgresSaver(pool)

    # Compile the workflow - NO interrupt_before since we use inline interrupt()
    app = workflow.compile(
        checkpointer=checkpointer
    )
    # Return the app and the pool so we can gracefully close it on shutdown
    return app, pool
