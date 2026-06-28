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
    # Return statically defined core agents for the n8n-style workflow builder
    return [
        {
            "id": "scraper_node",
            "name": "scraper_node",
            "description": "Scrapes the target website for firmographics and tech stack data.",
            "inputs": ["website", "company_name"],
            "outputs": ["firmographics", "tech_stack"],
            "is_core": True,
            "allowed_tools": ["WebSearch"]
        },
        {
            "id": "enricher_node",
            "name": "enricher_node",
            "description": "Enriches contact details and validates company information.",
            "inputs": ["firmographics"],
            "outputs": ["enriched_data"],
            "is_core": True,
            "allowed_tools": ["Crunchbase", "Clearbit"]
        },
        {
            "id": "score_node",
            "name": "score_node",
            "description": "Scores the prospect against the Ideal Customer Profile.",
            "inputs": ["firmographics", "tech_stack", "enriched_data"],
            "outputs": ["icp_score", "signals"],
            "is_core": True,
            "allowed_tools": []
        },
        {
            "id": "competitor_intel_node",
            "name": "competitor_intel_node",
            "description": "Finds competitors and mapping based on the tech stack.",
            "inputs": ["tech_stack"],
            "outputs": ["competitors"],
            "is_core": True,
            "allowed_tools": ["WebSearch"]
        },
        {
            "id": "cross_validator_node",
            "name": "cross_validator_node",
            "description": "Cross validates all gathered data for consistency.",
            "inputs": ["firmographics", "competitors"],
            "outputs": ["validation_notes", "confidence_score"],
            "is_core": True,
            "allowed_tools": []
        },
        {
            "id": "persona_matcher_node",
            "name": "persona_matcher_node",
            "description": "Matches the prospect to buyer personas.",
            "inputs": ["firmographics", "icp_score"],
            "outputs": ["matched_personas"],
            "is_core": True,
            "allowed_tools": []
        },
        {
            "id": "contact_finder_node",
            "name": "contact_finder_node",
            "description": "Finds specific contacts matching the buyer persona.",
            "inputs": ["matched_personas", "firmographics"],
            "outputs": ["contacts"],
            "is_core": True,
            "allowed_tools": ["LinkedIn", "Apollo", "EmployeeSearch"]
        },
        {
            "id": "outreach_generator_node",
            "name": "outreach_generator_node",
            "description": "Drafts personalized outreach sequences.",
            "inputs": ["contacts", "signals", "icp_score"],
            "outputs": ["draft_outreach"],
            "is_core": True,
            "allowed_tools": []
        },
        {
            "id": "summarizer_node",
            "name": "summarizer_node",
            "description": "Summarizes the entire prospect evaluation.",
            "inputs": ["icp_score", "draft_outreach"],
            "outputs": ["summary"],
            "is_core": True,
            "allowed_tools": []
        },
        {
            "id": "hitl_gateway_node",
            "name": "hitl_gateway_node",
            "description": "Gatekeeper for Human-In-The-Loop review.",
            "inputs": ["confidence_score", "validation_notes"],
            "outputs": ["status"],
            "is_core": True,
            "allowed_tools": []
        },
        {
            "id": "output_dispatcher_node",
            "name": "output_dispatcher_node",
            "description": "Dispatches the final JSON to webhooks or CRM.",
            "inputs": ["summary", "status"],
            "outputs": ["dispatched"],
            "is_core": True,
            "allowed_tools": []
        }
    ]


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
