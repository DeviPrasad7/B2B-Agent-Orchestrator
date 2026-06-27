from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import config, prospects, hitl, triggers, events, agents
from api.startup import lifespan
from core.settings import settings
from core.logging import setup_logging

# Initialize logging at startup
setup_logging(settings.LOG_LEVEL)

app = FastAPI(title="ICP Agent API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.FRONTEND_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(config.router)
app.include_router(prospects.router)
app.include_router(hitl.router)
app.include_router(triggers.router)
app.include_router(events.router)
app.include_router(agents.router)

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
