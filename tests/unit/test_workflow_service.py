import pytest
from unittest.mock import AsyncMock, patch
from services.workflow_service import WorkflowService

@pytest.fixture
def mock_graph_app():
    app = AsyncMock()
    app.ainvoke = AsyncMock(return_value={"overall_status": "COMPLETED"})
    return app

@pytest.mark.asyncio
async def test_start_workflow(mock_graph_app, memory_service, sample_company_data):
    # Setup mock
    ws = WorkflowService(mock_graph_app)
    
    state = {
        "prospect_id": "test-123",
        "data": {
            "company_name": sample_company_data["company_name"],
            "website_url": sample_company_data["website"]
        },
        "overall_status": "PENDING"
    }
    import asyncio
    import uuid
    pid = str(uuid.uuid4())
    state["prospect_id"] = pid
    await memory_service.save_prospect_state(state)
    thread_id = await ws.submit_prospect(state, pid)
    await asyncio.sleep(0.1) # Let the background task run
    
    assert thread_id is not None
    mock_graph_app.ainvoke.assert_called_once()
    
    prospect = await memory_service.get_prospect(thread_id)
    assert prospect is not None

@pytest.mark.asyncio
async def test_resume_workflow(mock_graph_app):
    ws = WorkflowService(mock_graph_app)
    import uuid
    thread_id = str(uuid.uuid4())
    import asyncio
    await ws.resume_with_hitl(thread_id, "APPROVED", {"score": 100})
    await asyncio.sleep(0.1) # Let background task run
    
    mock_graph_app.ainvoke.assert_called_once()
    
    call_args = mock_graph_app.ainvoke.call_args[0]
    command = call_args[0]
    assert command.resume["decision"] == "APPROVED"
    assert command.resume["corrections"] == {"score": 100}
