import uuid
from typing import Optional
from services.memory_service import MemoryService
from services.workflow_service import WorkflowService

class HITLService:
    def __init__(self, memory_service: MemoryService):
        self.memory_service = memory_service

    async def create_request(self, prospect_id: str, interrupt_data: dict) -> uuid.UUID:
        summary = interrupt_data.get("reason", "Manual review requested")
        request_id = await self.memory_service.create_hitl_request(prospect_id, summary)
        return request_id

    async def resolve_request(self, request_id: str, decision: str, corrections: Optional[dict]) -> None:
        try:
            rid = uuid.UUID(request_id)
        except ValueError:
            raise ValueError("Invalid request ID")
            
        # Need to get prospect_id to resume graph
        from models.database import HITLRequest, Prospect
        from sqlalchemy import select
        
        async with self.memory_service.session_factory() as session:
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
        await self.memory_service.resolve_hitl_request(rid, decision, corrections)
        
        # Resume workflow
        if prospect and prospect.workflow_thread_id:
            await WorkflowService.resume_with_hitl(prospect.workflow_thread_id, decision, corrections)
