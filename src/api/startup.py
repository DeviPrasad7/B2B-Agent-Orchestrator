import uuid
from contextlib import asynccontextmanager
from fastapi import FastAPI
from core.settings import settings
from core.logging import logger

from services.trigger_monitor import TriggerMonitor
from agent.graph import get_app
from agent.utils import Toolbox
from services.memory_service import MemoryService
from models.database import async_session, init_db
from services.config_service import ConfigService
from services.hitl_service import HITLService
from services.workflow_service import WorkflowService

async def _initialize_magic_seed(memory_service: MemoryService, workflow_service: WorkflowService):
    existing_prospects = await memory_service.list_prospects({"limit": 1})
    if not existing_prospects:
        magic_id = str(uuid.uuid4())
        magic_state = {
            "prospect_id": magic_id,
            "current_trigger_event": "manual_submission",
            "data": {
                "company_name": "Streamlit",
                "website_url": "https://streamlit.io",
                "firmographics": {
                    "tech_stack": [
                        {"technology": "Python", "category": "Language", "confidence": 0.99, "source": "magic_seed"},
                        {"technology": "React", "category": "Frontend", "confidence": 0.99, "source": "magic_seed"},
                        {"technology": "TypeScript", "category": "Language", "confidence": 0.99, "source": "magic_seed"}
                    ]
                }
            },
            "validation_notes": [],
            "confidence_score": 0.0,
            "overall_status": "PENDING",
            "human_override_payload": None,
            "executed_agents": ["enricher_node"],
            "errors": [],
            "has_conflict": False,
            "tech_detection_status": "PENDING",
            "simulate_failure": False
        }
        await memory_service.save_prospect_state(magic_state)
        await workflow_service.submit_prospect(magic_state, thread_id=magic_id)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database tables (safe to call every startup)
    if settings.APP_ENV != "test":
        await init_db()

    # Initialize LangGraph workflow dependencies
    from services.llm_service import LLMService
    from services.scraping_service import ScrapingService
    from services.enrichment_service import EnrichmentService
    
    toolbox = Toolbox(
        llm_service=LLMService(),
        scraping_service=ScrapingService(),
        enrichment_service=EnrichmentService()
    )
    
    memory_service = MemoryService(async_session)
    
    async with async_session() as session:
        config_service = ConfigService(session)
        
        # Create configuration dictionary to pass to agents
        config_dict = {
            "icp": await config_service.get_icp(),
            "personas": await config_service.get_persona()
        }
    
    graph_app, pool = await get_app(toolbox, memory_service, config_dict)
    app.state.graph_app = graph_app
    app.state.checkpointer_pool = pool
    app.state.hitl_service = HITLService(memory_service)
    
    # Inject graph_app into WorkflowService first, as TriggerMonitor needs it
    app.state.workflow_service = WorkflowService(graph_app, app.state.hitl_service)
    app.state.hitl_service.workflow_service = app.state.workflow_service
    
    # Instantiate TriggerMonitor and auto-start background polling
    app.state.trigger_monitor = TriggerMonitor(toolbox, app.state.workflow_service)
    app.state.trigger_monitor.start()

    # Make toolbox accessible to endpoints (e.g. events)
    app.state.toolbox = toolbox

    # Make toolbox accessible to endpoints (e.g. events)
    app.state.toolbox = toolbox

    # Insert Magic Seed Prospect if empty
    await _initialize_magic_seed(memory_service, app.state.workflow_service)

    try:
        yield
    finally:
        # Gracefully shutdown
        if hasattr(app.state, "trigger_monitor"):
            app.state.trigger_monitor.stop()
            
        if hasattr(app.state, "checkpointer_pool"):
            pool = app.state.checkpointer_pool
            if pool:
                logger.info("Closing checkpointer pool")
                await pool.close()
