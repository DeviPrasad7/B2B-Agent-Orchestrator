import asyncio
from agent.state import GraphState
from models.database import async_session
from services.config_service import ConfigService
import structlog

logger = structlog.get_logger()

class WorkflowService:
    """Wrapper to run the LangGraph workflow."""
    
    _app = None
    _hitl_service = None

    @classmethod
    def set_app(cls, app):
        cls._app = app
        
    @classmethod
    def set_hitl_service(cls, hitl_service):
        cls._hitl_service = hitl_service

    @staticmethod
    async def submit_prospect(state: GraphState, thread_id: str):
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
                await WorkflowService._app.ainvoke(configured_state, config=config)
                
                # Check if the graph paused due to an interrupt
                state_snapshot = await WorkflowService._app.aget_state(config)
                if state_snapshot.next:
                    logger.info("Workflow paused (interrupt) for prospect", thread_id=thread_id)
                    interrupt_data = {}
                    for task in state_snapshot.tasks:
                        if task.interrupts:
                            interrupt_data = task.interrupts[0].value
                            break
                    
                    if WorkflowService._hitl_service:
                        await WorkflowService._hitl_service.create_request(thread_id, interrupt_data)
                    else:
                        logger.error("HITLService not configured in WorkflowService")
                else:
                    final_state = state_snapshot.values
                    logger.info("Workflow completed", thread_id=thread_id, final_status=final_state.get("overall_status"))
            except Exception as e:
                logger.error("Workflow failed", thread_id=thread_id, error=str(e))

        asyncio.create_task(run_workflow(state))
        return thread_id

    @staticmethod
    async def resume_with_hitl(thread_id: str, decision: str, corrections: dict):
        async def run_resume():
            config = {"configurable": {"thread_id": thread_id}}
            logger.info("Resuming workflow", thread_id=thread_id, decision=decision)
            try:
                from langgraph.types import Command
                resume_payload = {"decision": decision}
                if corrections:
                    resume_payload["corrections"] = corrections
                    
                await WorkflowService._app.ainvoke(Command(resume=resume_payload), config=config)
                
                state_snapshot = await WorkflowService._app.aget_state(config)
                if not state_snapshot.next:
                    logger.info("Workflow completed after resume", thread_id=thread_id)
                else:
                    logger.warning("Workflow paused again unexpectedly", thread_id=thread_id)
            except Exception as e:
                logger.error("Workflow resume failed", thread_id=thread_id, error=str(e))

        asyncio.create_task(run_resume())
