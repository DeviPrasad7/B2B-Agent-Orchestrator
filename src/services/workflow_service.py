import asyncio
from agent.state import GraphState
from models.database import async_session
from services.config_service import ConfigService
from core.logging import logger

class WorkflowService:
    """Wrapper to run the LangGraph workflow.

    Instance-based approach. Should be stored on app.state.workflow_service
    or injected via dependencies.
    """

    def __init__(self, graph_app, hitl_service=None):
        """Instance constructor."""
        self._app = graph_app
        self._hitl_service = hitl_service
        self._tasks = set()

    def set_hitl_service(self, hitl_service):
        self._hitl_service = hitl_service

    async def submit_prospect(self, state: GraphState, thread_id: str):
        """
        Submits a prospect state to the LangGraph workflow asynchronously.
        """
        async with async_session() as session:
            config_service = ConfigService(session)
            icp = await config_service.get_icp()
            persona = await config_service.get_persona()
            thresholds = await config_service.get_thresholds()
            
            state["config"] = {
                "icp": icp.model_dump() if icp else {},
                "persona": persona.model_dump() if persona else {},
                "thresholds": thresholds.model_dump() if thresholds else {}
            }
            
        async def run_workflow(configured_state: GraphState):
            logger.info("Starting workflow for prospect", thread_id=thread_id)
            config = {"configurable": {"thread_id": thread_id}}
            try:
                if self._app is None:
                    raise RuntimeError("WorkflowService graph app is not initialized")
                    
                from core.pubsub import pubsub_broker
                async for event in self._app.astream_events(configured_state, config=config, version="v2"):
                    await pubsub_broker.publish(thread_id, event)
                
                # Check if the graph paused due to an interrupt
                state_snapshot = await self._app.aget_state(config)
                if state_snapshot.next:
                    logger.info("Workflow paused (interrupt) for prospect", thread_id=thread_id)
                    interrupt_data = {}
                    for task in state_snapshot.tasks:
                        if task.interrupts:
                            interrupt_data = task.interrupts[0].value
                            break
                    
                    if self._hitl_service:
                        await self._hitl_service.create_request(thread_id, interrupt_data)
                    else:
                        logger.error("HITLService not configured in WorkflowService")
                else:
                    final_state = state_snapshot.values
                    logger.info("Workflow completed", thread_id=thread_id, final_status=final_state.get("overall_status"))
            except Exception as e:
                logger.error("Workflow failed", thread_id=thread_id, error=str(e))

        task = asyncio.create_task(run_workflow(state))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)
        return thread_id

    async def resume_with_hitl(self, thread_id: str, decision: str, corrections: dict):
        async def run_resume():
            config = {"configurable": {"thread_id": thread_id}}
            logger.info("Resuming workflow", thread_id=thread_id, decision=decision)
            try:
                from langgraph.types import Command
                from core.pubsub import pubsub_broker
                resume_payload = {"decision": decision}
                if corrections:
                    resume_payload["corrections"] = corrections
                    
                async for event in self._app.astream_events(Command(resume=resume_payload), config=config, version="v2"):
                    await pubsub_broker.publish(thread_id, event)
                
                state_snapshot = await self._app.aget_state(config)
                if not state_snapshot.next:
                    logger.info("Workflow completed after resume", thread_id=thread_id)
                else:
                    logger.warning("Workflow paused again unexpectedly", thread_id=thread_id)
            except Exception as e:
                logger.error("Workflow resume failed", thread_id=thread_id, error=str(e))

        task = asyncio.create_task(run_resume())
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)
