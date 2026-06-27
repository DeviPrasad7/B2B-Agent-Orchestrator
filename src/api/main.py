from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import config, prospects, hitl, triggers
from services.trigger_monitor import TriggerMonitor
from agent.graph import setup_graph
from agent.utils import Toolbox, MemoryStore

# Global trigger monitor instance
trigger_monitor = TriggerMonitor()

# Initialize LangGraph workflow dependencies
toolbox = Toolbox()
memory_store = MemoryStore()
setup_graph(toolbox, memory_store)

app = FastAPI(title="ICP Agent API", version="1.0.0")

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
