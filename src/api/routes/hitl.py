from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional
from models.schemas import HITLRequestDetail
from services.memory_service import MemoryService
from models.database import async_session
from sqlalchemy.ext.asyncio import AsyncSession
import uuid
from api.dependencies import get_memory_service

router = APIRouter(prefix="/api/hitl", tags=["hitl"])

@router.get("/pending", response_model=List[HITLRequestDetail])
async def list_pending_hitl(memory_service: MemoryService = Depends(get_memory_service)):
    requests = await memory_service.get_pending_hitl_requests()
    return [
        HITLRequestDetail(
            id=r.id,
            display_id=r.display_id,
            prospect_id=r.prospect_id,
            summary=r.summary,
            decision=r.decision,
            corrections=r.corrections,
            created_at=r.created_at,
            resolved_at=r.resolved_at
        ) for r in requests
    ]

@router.get("/{request_id}", response_model=HITLRequestDetail)
async def get_hitl_request(request_id: str, memory_service: MemoryService = Depends(get_memory_service)):
    try:
        rid = uuid.UUID(request_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid request ID format")
        
    from sqlalchemy import select
    from models.database import HITLRequest
    
    async with memory_service.session_factory() as session:
        result = await session.execute(
            select(HITLRequest).where(HITLRequest.id == rid)
        )
        r = result.scalar_one_or_none()
    
    if not r:
        raise HTTPException(status_code=404, detail="Request not found")
        
    return HITLRequestDetail(
        id=r.id,
        display_id=r.display_id,
        prospect_id=r.prospect_id,
        summary=r.summary,
        decision=r.decision,
        corrections=r.corrections,
        created_at=r.created_at,
        resolved_at=r.resolved_at
    )

from pydantic import BaseModel
from fastapi import Request
class HITLDecisionRequest(BaseModel):
    corrections: Optional[dict] = None

@router.post("/{request_id}/approve")
async def approve_hitl(request_id: str, request: Request, req: HITLDecisionRequest = None):
    hitl_service = request.app.state.hitl_service
    corrections = req.corrections if req else None
    try:
        await hitl_service.resolve_request(request_id, "APPROVED", corrections)
        return {"status": "success", "decision": "APPROVED"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{request_id}/reject")
async def reject_hitl(request_id: str, request: Request, req: HITLDecisionRequest = None):
    hitl_service = request.app.state.hitl_service
    corrections = req.corrections if req else None
    try:
        await hitl_service.resolve_request(request_id, "REJECTED", corrections)
        return {"status": "success", "decision": "REJECTED"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
