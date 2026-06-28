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
    
    # Instantiate TriggerMonitor but DO NOT auto-start background polling
    app.state.trigger_monitor = TriggerMonitor(toolbox, app.state.workflow_service)

    # Make toolbox accessible to endpoints (e.g. events)
    app.state.toolbox = toolbox

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
