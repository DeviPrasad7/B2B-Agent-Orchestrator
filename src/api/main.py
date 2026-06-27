from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import config, prospects, hitl, triggers
from services.trigger_monitor import TriggerMonitor
from agent.graph import get_app
from agent.utils import Toolbox
from services.memory_service import MemoryService
from models.database import async_session

# Global trigger monitor instance
trigger_monitor = TriggerMonitor()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize LangGraph workflow dependencies
    toolbox = Toolbox()
    
    # Use an async session context block? No, MemoryService needs a session but it doesn't need to be closed immediately if we reuse it, 
    # wait, MemoryService expects a session. The nodes use the same memory_service. 
    # We shouldn't reuse a single SQLAlchemy session for the entire application lifetime as it's not thread/task safe. 
    # Let's check how MemoryService is designed. It takes a session in __init__. 
    # Actually, in the old `MemoryStore`, it created a new session for each operation:
    # `async with async_session() as session: service = MemoryService(session)`
    
    # Wait, if MemoryService takes a session, passing a single instance to all nodes is dangerous if concurrent nodes run.
    # But wait, the user's plan:
    # "Create a single instance of MemoryService (with a database session factory) at application startup and reuse it across all nodes."
    # Wait, the prompt said:
    # "Create a single instance of MemoryService (with a database session factory) at application startup and reuse it across all nodes."
    # MemoryService currently takes a session, not a factory! Let's check `services/memory_service.py` -> `def __init__(self, session: AsyncSession):`
    # Hmm, if I pass a single MemoryService to all nodes, they share the same session. That's what the user asked. Let's do it.
    
    session = async_session()
    memory_service = MemoryService(session)
    
    graph_app = await get_app(toolbox, memory_service)
    app.state.graph_app = graph_app
    
    # Inject graph_app into WorkflowService to avoid circular imports
    from services.workflow_service import WorkflowService
    WorkflowService.set_app(graph_app)
    
    yield
    
    await session.close()

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
