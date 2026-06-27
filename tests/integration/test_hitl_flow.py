import pytest
from services.workflow_service import WorkflowService
from agent.graph import get_app
from models.database import Prospect

@pytest.mark.asyncio
async def test_hitl_flow_execution(mock_toolbox, memory_service, hitl_service, sample_icp, sample_personas, async_session):
    # Setup graph app manually with mocks for end-to-end testing
    config_dict = {
        "icp": sample_icp,
        "personas": sample_personas
    }
    
    graph_app, pool = await get_app(mock_toolbox, memory_service, config_dict)
    ws = WorkflowService(graph_app, hitl_service)
    hitl_service.workflow_service = ws
    
    # Run the workflow with a company name that forces HITL or mock the planner to go to HITL
    def llm_routing_side_effect(prompt, fallback, require_json=False):
        if "Available Agents:" in prompt:
            # Safely check what has been executed
            # Find the Executed Agents list in the prompt
            import re
            match = re.search(r"- Executed Agents:\s*(\[.*?\])", prompt)
            executed = match.group(1) if match else "[]"
            
            if "'hitl_gateway_node'" not in executed:
                return '{"next_node": "hitl_gateway_node"}'
            elif "'output_dispatcher_node'" not in executed:
                return '{"next_node": "output_dispatcher_node"}'
            else:
                return '{"next_node": "__end__"}'
        return '{"decision": "APPROVE"}'
    
    mock_toolbox.generate_text.side_effect = llm_routing_side_effect
    
    import asyncio
    import uuid
    pid = str(uuid.uuid4())
    state = {
        "prospect_id": pid,
        "data": {
            "company_name": "Need Approval Corp",
            "website_url": ""
        },
        "overall_status": "PENDING"
    }
    await memory_service.save_prospect_state(state)
    thread_id = await ws.submit_prospect(state, pid)
    await asyncio.sleep(0.5)
    
    # The workflow should be paused and status should be PENDING_HUMAN
    prospect = await memory_service.get_prospect(pid)
    
    assert prospect.status == "PENDING_HUMAN"
    
    # Verify HITL request was created
    pending_reqs = await memory_service.get_pending_hitl_requests()
    assert len(pending_reqs) == 1
    req = pending_reqs[0]
    
    # Resume the workflow via approval
    await ws.resume_with_hitl(thread_id, "APPROVED", {"score": 90})
    await asyncio.sleep(0.5)
    if pool:
        await pool.close()
    
    # Check updated status
    prospect = await memory_service.get_prospect(pid)
    # the hitl gateway node will set overall_status to APPROVED if APPROVED
    assert prospect.status == "APPROVED"
