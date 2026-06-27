import pytest
from services.workflow_service import WorkflowService
from agent.graph import get_app

@pytest.mark.asyncio
async def test_full_workflow_execution(mock_toolbox, memory_service, sample_company_data, sample_icp, sample_personas):
    # Setup graph app manually with mocks for end-to-end testing
    config_dict = {
        "icp": sample_icp,
        "personas": sample_personas
    }
    
    # To prevent endless loops in testing, ensure mock planner routes efficiently
    # Instead of full mock, let's use a side_effect on generate_text to simulate planner routing
    def llm_routing_side_effect(prompt, fallback):
        if "Available Agents:" in prompt:
            if "score_node" not in prompt:
                pass # just a generic check
            
            # Simple deterministic routing for the mock LLM
            import re
            match = re.search(r"- Executed Agents:\s*(\[.*?\])", prompt)
            executed = match.group(1) if match else "[]"
            
            if "'enricher_node'" not in executed:
                return '{"next_node": "enricher_node"}'
            elif "'score_node'" not in executed:
                return '{"next_node": "score_node"}'
            else:
                return '{"next_node": "__end__"}'
        return '{"decision": "APPROVE"}'

    mock_toolbox.generate_text.side_effect = llm_routing_side_effect
    
    graph_app, pool = await get_app(mock_toolbox, memory_service, config_dict)
    ws = WorkflowService(graph_app)
    
    import asyncio
    import uuid
    # Run the workflow
    pid = str(uuid.uuid4())
    state = {
        "prospect_id": pid,
        "data": {
            "company_name": sample_company_data["company_name"],
            "website_url": sample_company_data["website"]
        },
        "overall_status": "PENDING"
    }
    await memory_service.save_prospect_state(state)
    thread_id = await ws.submit_prospect(state, pid)
    
    # Wait for completion
    await asyncio.sleep(0.5)
    if pool:
        await pool.close()
    
    assert thread_id is not None
    
    # Verify memory
    prospect = await memory_service.get_prospect(pid)
    assert prospect is not None
    assert prospect.company_name == sample_company_data["company_name"]
