from fastapi import APIRouter, Depends, Query, HTTPException, Request
from typing import List, Optional
from uuid import uuid4
from models.schemas import ProspectSummary, ProspectDetail
from services.memory_service import MemoryService
from services.workflow_service import WorkflowService
from models.database import async_session
from sqlalchemy.ext.asyncio import AsyncSession
from agent.state import GraphState
from api.dependencies import get_memory_service
from sse_starlette.sse import EventSourceResponse
from core.pubsub import pubsub_broker
import json
import asyncio

router = APIRouter(prefix="/api/prospects", tags=["prospects"])

@router.get("", response_model=List[ProspectSummary])
async def list_prospects(
    status: Optional[str] = Query(None),
    company_name: Optional[str] = Query(None),
    limit: int = Query(100),
    offset: int = Query(0),
    memory_service: MemoryService = Depends(get_memory_service)
):
    filters = {
        "status": status,
        "company_name": company_name,
        "limit": limit,
        "offset": offset
    }
    return await memory_service.list_prospects(filters)

@router.get("/{prospect_id}", response_model=ProspectDetail)
async def get_prospect(prospect_id: str, memory_service: MemoryService = Depends(get_memory_service)):
    prospect = await memory_service.get_prospect(prospect_id)
    if not prospect:
        raise HTTPException(status_code=404, detail="Prospect not found")
        
    return ProspectDetail(
        id=prospect.id,
        display_id=prospect.display_id,
        company_name=prospect.company_name,
        website=prospect.website,
        status=prospect.status,
        state_json=prospect.state_json,
        created_at=prospect.created_at,
        updated_at=prospect.updated_at,
        workflow_thread_id=prospect.workflow_thread_id
    )

from pydantic import BaseModel
class CreateProspectRequest(BaseModel):
    company_name: str
    website: Optional[str] = None
    trigger_event: str = "manual_submission"
    simulate_failure: bool = False

@router.post("")
async def create_prospect(
    req: CreateProspectRequest, 
    request: Request,
    memory_service: MemoryService = Depends(get_memory_service)
):
    prospect_id = str(uuid4())
    state: GraphState = {
        "prospect_id": prospect_id,
        "current_trigger_event": req.trigger_event,
        "data": {
            "company_name": req.company_name,
            "website_url": req.website
        },
        "validation_notes": [],
        "confidence_score": 0.0,
        "overall_status": "PENDING",
        "human_override_payload": None,
        "executed_agents": [],
        "errors": [],
        "has_conflict": False,
        "tech_detection_status": "PENDING",
        "simulate_failure": req.simulate_failure
    }
    
    # Save initial state
    await memory_service.save_prospect_state(state)
    
    # Submit to workflow
    await request.app.state.workflow_service.submit_prospect(state, thread_id=prospect_id)
    
    return {"status": "success", "prospect_id": prospect_id}

@router.get("/{prospect_id}/stream")
async def stream_prospect_events(request: Request, prospect_id: str):
    async def event_generator():
        queue = await pubsub_broker.subscribe(prospect_id)
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=1.0)
                    yield {"data": json.dumps(event, default=str)}
                except asyncio.TimeoutError:
                    continue
        finally:
            pubsub_broker.unsubscribe(prospect_id, queue)
            
    return EventSourceResponse(event_generator())

