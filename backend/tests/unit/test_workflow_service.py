import asyncio
import uuid

import pytest
from unittest.mock import AsyncMock, MagicMock

from services.workflow_service import WorkflowService


@pytest.fixture
def mock_graph_app():
    """Mock LangGraph app that returns a proper async iterator for astream_events."""
    app = MagicMock()

    async def _mock_astream_events(*args, **kwargs):
        # Yield a minimal terminal event so the workflow loop finishes cleanly
        yield {"event": "on_chain_end", "data": {"output": {"overall_status": "COMPLETED"}}}

    app.astream_events = _mock_astream_events
    return app


@pytest.mark.asyncio
async def test_start_workflow(mock_graph_app, memory_service, sample_company_data):
    ws = WorkflowService(mock_graph_app)

    pid = str(uuid.uuid4())
    state = {
        "prospect_id": pid,
        "data": {
            "company_name": sample_company_data["company_name"],
            "website_url": sample_company_data["website"],
        },
        "overall_status": "PENDING",
    }

    await memory_service.save_prospect_state(state)
    thread_id = await ws.submit_prospect(state, pid)
    await asyncio.sleep(0.2)  # Allow background task to complete

    assert thread_id is not None
    assert thread_id == pid

    prospect = await memory_service.get_prospect(thread_id)
    assert prospect is not None


@pytest.mark.asyncio
async def test_resume_workflow(mock_graph_app):
    """Resume sends the correct payload key ('action') to the graph Command."""
    captured_args = []

    async def _mock_astream_events(*args, **kwargs):
        captured_args.append((args, kwargs))
        yield {"event": "on_chain_end", "data": {"output": {}}}

    mock_graph_app.astream_events = _mock_astream_events

    ws = WorkflowService(mock_graph_app)
    thread_id = str(uuid.uuid4())

    await ws.resume_with_hitl(thread_id, "APPROVED", {"score": 100})
    await asyncio.sleep(0.2)

    assert len(captured_args) == 1
    # The first positional arg to astream_events should be the LangGraph Command
    from langgraph.types import Command
    command = captured_args[0][0][0]
    assert isinstance(command, Command)
    # Key is "action" (aligned with hitl_gateway.py which reads response.get("action"))
    assert command.resume["action"] == "APPROVED"
    assert command.resume["edits"] == {"score": 100}
