from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import config, prospects, hitl, triggers
from services.trigger_monitor import TriggerMonitor
from agent.graph import get_app
from agent.utils import Toolbox
from services.memory_service import MemoryService
from models.database import async_session, init_db
from core.settings import settings
from services.config_service import ConfigService
from core.logging import setup_logging
from services.hitl_service import HITLService

# Initialize logging at startup
setup_logging(settings.LOG_LEVEL)

# Global trigger monitor instance removed (moved to state)

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
    
    graph_app = await get_app(toolbox, memory_service, config_dict)
    app.state.graph_app = graph_app
    app.state.hitl_service = HITLService(memory_service)
    
    # Instantiate TriggerMonitor
    app.state.trigger_monitor = TriggerMonitor(toolbox)
    
    # Inject graph_app into WorkflowService to avoid circular imports
    from services.workflow_service import WorkflowService
    WorkflowService.set_app(graph_app)
    WorkflowService.set_hitl_service(app.state.hitl_service)
    
    yield

app = FastAPI(title="ICP Agent API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(config.router)
app.include_router(prospects.router)
app.include_router(hitl.router)
app.include_router(triggers.router)

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
