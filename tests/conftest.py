import pytest
import pytest_asyncio
import json
import os
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from httpx import AsyncClient, ASGITransport

# Set environment variable for test
os.environ["APP_ENV"] = "test"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///file:testdb?mode=memory&cache=shared&uri=true"
# Fallback to sqlite if needed: "sqlite+aiosqlite:///:memory:"

from models.database import Base
from services.memory_service import MemoryService
from services.config_service import ConfigService
from services.hitl_service import HITLService
from services.workflow_service import WorkflowService
from agent.utils import Toolbox
from api.main import app
from agent.graph import get_app

# --- Database Fixtures ---

@pytest_asyncio.fixture(scope="function")
async def async_engine():
    engine = create_async_engine(
        "sqlite+aiosqlite:///file:testdb?mode=memory&cache=shared&uri=true",
        echo=False,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    yield engine
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()

@pytest_asyncio.fixture(scope="function")
def session_maker(async_engine):
    return async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)

@pytest_asyncio.fixture(scope="function")
async def async_session(session_maker):
    async with session_maker() as session:
        yield session

# --- Mock Fixtures ---

@pytest.fixture
def mock_toolbox():
    toolbox = MagicMock(spec=Toolbox)
    
    # Mock llm_service
    toolbox.llm_service = AsyncMock()
    toolbox.llm_service.generate_json = AsyncMock(return_value={"decision": "APPROVE"})
    toolbox.llm_service.generate_text = AsyncMock(return_value="Mocked LLM text.")
    
    # Mock scraping_service
    toolbox.scraping_service = AsyncMock()
    toolbox.scraping_service.scrape_company_website = AsyncMock(return_value={"content": "Mocked website content"})
    
    # Mock enrichment_service
    toolbox.enrichment_service = AsyncMock()
    toolbox.enrichment_service.find_contacts = AsyncMock(return_value=[{"name": "John Doe", "title": "CTO"}])
    
    class MockCB:
        name = "TestCorp"
        employeeCount = 100
        revenue = 1000000
        industries = ["B2B SaaS"]
    toolbox.fetch_crunchbase = AsyncMock(return_value=MockCB())
    toolbox.scrape_linkedin = AsyncMock(return_value={"location": "San Francisco"})
    
    # Mock circuit breaker
    import asyncio
    async def mock_execute(f, *args, **kwargs):
        if asyncio.iscoroutinefunction(f):
            return await f(*args, **kwargs)
        return f(*args, **kwargs)
        
    toolbox.circuit_breaker = MagicMock()
    toolbox.circuit_breaker.execute = AsyncMock(side_effect=mock_execute)
    toolbox.circuit_breaker.check_health = MagicMock(return_value={"status": "healthy"})
    
    return toolbox

# --- Service Fixtures ---

@pytest.fixture
def memory_service(session_maker):
    return MemoryService(session_factory=session_maker)

@pytest.fixture
def config_service(async_session):
    return ConfigService(async_session)

@pytest.fixture
def hitl_service(memory_service):
    return HITLService(memory_service)

@pytest_asyncio.fixture
async def workflow_service(mock_toolbox, memory_service, hitl_service):
    # Workflow service needs a graph app. We will initialize it with mocked components.
    config_dict = {"icp": {}, "personas": []}
    graph_app, pool = await get_app(mock_toolbox, memory_service, config_dict)
    ws = WorkflowService(graph_app, hitl_service)
    yield ws
    if pool:
        await pool.close()



# --- API Fixtures ---

@pytest_asyncio.fixture
async def app_client(async_session, mock_toolbox, hitl_service, memory_service):
    # We might need to override dependencies here if FastAPI uses Depends,
    # but the app relies on lifespan and global state mostly.
    config_dict = {"icp": {}, "personas": []}
    graph_app, pool = await get_app(mock_toolbox, memory_service, config_dict)
    
    app.state.graph_app = graph_app
    app.state.checkpointer_pool = pool
    app.state.hitl_service = hitl_service
    app.state.workflow_service = WorkflowService(graph_app, hitl_service)
    hitl_service.workflow_service = app.state.workflow_service
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client
        
    if pool:
        await pool.close()

# --- Data Fixtures ---

@pytest.fixture
def sample_icp():
    path = os.path.join(os.path.dirname(__file__), "fixtures", "sample_icp.json")
    with open(path, "r") as f:
        return json.load(f)

@pytest.fixture
def sample_personas():
    path = os.path.join(os.path.dirname(__file__), "fixtures", "sample_personas.json")
    with open(path, "r") as f:
        return json.load(f)

@pytest.fixture
def sample_company_data():
    path = os.path.join(os.path.dirname(__file__), "fixtures", "sample_company_data.json")
    with open(path, "r") as f:
        return json.load(f)
