from fastapi import APIRouter, Depends, HTTPException, Request
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models.database import CustomAgent
from models.schemas import CustomAgentCreate, CustomAgentDetail
from api.dependencies import get_session
import uuid
import asyncio
import json
from datetime import datetime, timezone
from fastapi.responses import StreamingResponse

router = APIRouter(prefix="/api/agents", tags=["agents"])

@router.get("/tools", response_model=List[str])
async def list_available_tools():
    return ["WebSearch", "Crunchbase", "LinkedIn", "EmployeeSearch", "Serper", "Clearbit", "Apollo"]

@router.delete("/debug/clear-db", status_code=200)
async def clear_database(session: AsyncSession = Depends(get_session)):
    from sqlalchemy import text
    await session.execute(text("TRUNCATE TABLE prospects CASCADE;"))
    await session.execute(text("TRUNCATE TABLE hitl_requests CASCADE;"))
    await session.execute(text("TRUNCATE TABLE workflows CASCADE;"))
    await session.execute(text("TRUNCATE TABLE custom_agents CASCADE;"))
    await session.execute(text("TRUNCATE TABLE processed_events CASCADE;"))
    await session.commit()
    return {"message": "All data cleared successfully."}

@router.get("/core")
async def list_core_agents():
    # Return dynamically defined core agents for the n8n-style workflow builder
    core_agents = []
    
    # Map inputs and outputs for visual aesthetics
    io_map = {
        "monitor_node": (["website", "company_name"], ["firmographics"]),
        "tech_stack_detector_node": (["website", "company_name"], ["tech_stack"]),
        "enricher_node": (["firmographics"], ["enriched_data"]),
        "score_node": (["firmographics", "tech_stack", "enriched_data"], ["icp_score", "signals"]),
        "competitor_intel_node": (["tech_stack"], ["competitors"]),
        "cross_validator_node": (["firmographics", "competitors"], ["validation_notes", "confidence_score"]),
        "persona_matcher_node": (["firmographics", "icp_score"], ["matched_personas"]),
        "contact_finder_node": (["matched_personas", "firmographics"], ["contacts"]),
        "outreach_generator_node": (["contacts", "signals", "icp_score"], ["draft_outreach"]),
        "summarizer_node": (["icp_score", "draft_outreach"], ["summary"]),
        "hitl_gateway_node": (["confidence_score", "validation_notes"], ["status"]),
        "output_dispatcher_node": (["summary", "status"], ["dispatched"]),
        "consolidation_node": (["*"], ["consolidated_data"]),
        "researcher_node": (["company_name"], ["research_data"]),
        "ender_node": (["*"], ["summary", "status", "dispatched"]),
    }
    
    try:
        from agent.registry import registry
        for name in registry.list_agents():
            if name not in ["dynamic_planner_node", "dynamic_agent_executor"]:
                desc = registry.get_description(name)
                inputs, outputs = io_map.get(name, ([], []))
                core_agents.append({
                    "id": name,
                    "name": name,
                    "description": desc,
                    "inputs": inputs,
                    "outputs": outputs,
                    "is_core": True,
                    "allowed_tools": []
                })
    except Exception as e:
        import traceback
        traceback.print_exc()
    return core_agents

@router.get("", response_model=List[CustomAgentDetail])
async def list_agents(session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(CustomAgent))
    agents = result.scalars().all()
    return [
        CustomAgentDetail(
            id=a.id,
            name=a.name,
            description=a.description,
            system_prompt=a.system_prompt,
            allowed_tools=a.allowed_tools or [],
            created_at=a.created_at,
        )
        for a in agents
    ]

@router.post("", response_model=CustomAgentDetail)
async def create_agent(agent: CustomAgentCreate, session: AsyncSession = Depends(get_session)):
    new_agent = CustomAgent(
        name=agent.name,
        description=agent.description,
        system_prompt=agent.system_prompt,
        allowed_tools=agent.allowed_tools
    )
    session.add(new_agent)
    try:
        await session.commit()
        await session.refresh(new_agent)
    except Exception:
        await session.rollback()
        raise HTTPException(status_code=400, detail=f"Agent '{agent.name}' already exists or DB constraint violated.")

    return CustomAgentDetail(
        id=new_agent.id,
        name=new_agent.name,
        description=new_agent.description,
        system_prompt=new_agent.system_prompt,
        allowed_tools=new_agent.allowed_tools or [],
        created_at=new_agent.created_at,
    )


@router.delete("/{agent_id}", status_code=204)
async def delete_agent(agent_id: str, session: AsyncSession = Depends(get_session)):
    try:
        aid = uuid.UUID(agent_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid agent ID format")

    result = await session.execute(select(CustomAgent).where(CustomAgent.id == aid))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    await session.delete(agent)
    await session.commit()

@router.get("/{agent_id}/logs/stream")
async def stream_agent_logs(agent_id: str, request: Request, session: AsyncSession = Depends(get_session)):
    try:
        aid = uuid.UUID(agent_id)
        result = await session.execute(select(CustomAgent).where(CustomAgent.id == aid))
        agent = result.scalar_one_or_none()
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found.")
    except Exception:
        raise HTTPException(status_code=404, detail="Invalid agent ID.")

    async def log_generator():
        # Yield an initial boot message so the terminal looks alive
        msg = f"[{agent.name}] Initialized. Awaiting real-time tool execution logs..."
        payload = json.dumps({"timestamp": datetime.now(timezone.utc).isoformat(), "level": "INFO", "message": msg})
        yield f"data: {payload}\n\n"
        
        last_event_idx = -1
        toolbox = getattr(request.app.state, 'toolbox', None)
        
        while True:
            if toolbox and hasattr(toolbox, 'event_store'):
                current_events = toolbox.event_store
                if len(current_events) > last_event_idx + 1:
                    # Look at new events
                    start_idx = max(0, last_event_idx + 1)
                    new_events = current_events[start_idx:]
                    last_event_idx = len(current_events) - 1
                    
                    for event in new_events:
                        if event.get("type") == "CustomAgentLog":
                            payload_data = event.get("payload", {})
                            if payload_data.get("agent_id") == agent_id:
                                level = payload_data.get("level", "INFO")
                                msg_text = f"[{agent.name}] {payload_data.get('message', '')}"
                                
                                out_payload = json.dumps({
                                    "timestamp": datetime.now(timezone.utc).isoformat(),
                                    "level": level,
                                    "message": msg_text
                                })
                                yield f"data: {out_payload}\n\n"
            
            await asyncio.sleep(1.0) # Check every second

    return StreamingResponse(log_generator(), media_type="text/event-stream")
