import uuid
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from services.memory_service import MemoryService
from services.workflow_service import WorkflowService
from models.database import async_session

class HITLService:
    @staticmethod
    async def create_request(prospect_id: str, interrupt_data: dict) -> uuid.UUID:
        memory_service = MemoryService(async_session)
        summary = interrupt_data.get("reason", "Manual review requested")
        request_id = await memory_service.create_hitl_request(prospect_id, summary)
        return request_id

    @staticmethod
    async def resolve_request(request_id: str, decision: str, corrections: Optional[dict]) -> None:
        memory_service = MemoryService(async_session)
        
        try:
            rid = uuid.UUID(request_id)
        except ValueError:
            raise ValueError("Invalid request ID")
            
        # Need to get prospect_id to resume graph
        from models.database import HITLRequest, Prospect
        from sqlalchemy import select
        
        async with async_session() as session:
            result = await session.execute(
                select(HITLRequest).where(HITLRequest.id == rid)
            )
            hitl = result.scalar_one_or_none()
            if not hitl:
                raise ValueError("HITL request not found")
                
            prospect_result = await session.execute(
                select(Prospect).where(Prospect.id == hitl.prospect_id)
            )
            prospect = prospect_result.scalar_one_or_none()
            
            # Update DB
            await memory_service.resolve_hitl_request(rid, decision, corrections)
            
            # Resume workflow
            if prospect and prospect.workflow_thread_id:
                await WorkflowService.resume_with_hitl(prospect.workflow_thread_id, decision, corrections)
