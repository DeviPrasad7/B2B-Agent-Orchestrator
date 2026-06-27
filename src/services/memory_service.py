import uuid
from typing import Any, Optional, List, Callable
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from models.database import Prospect, HITLRequest, ProcessedEvent, get_utc_now
from models.schemas import ProspectSummary

class MemoryService:
    def __init__(self, session_factory: Callable[[], AsyncSession]):
        self.session_factory = session_factory

    async def has_event_been_processed(self, event_hash: str) -> bool:
        async with self.session_factory() as session:
            result = await session.execute(
                select(ProcessedEvent).where(ProcessedEvent.event_hash == event_hash)
            )
            return result.scalar_one_or_none() is not None

    async def mark_event_processed(self, event_hash: str, prospect_id: str, status: str = "completed") -> None:
        async with self.session_factory() as session:
            event = ProcessedEvent(event_hash=event_hash, prospect_id=prospect_id, status=status)
            session.add(event)
            await session.commit()

    async def update_event_status(self, event_hash: str, status: str) -> None:
        from sqlalchemy import update
        async with self.session_factory() as session:
            await session.execute(
                update(ProcessedEvent)
                .where(ProcessedEvent.event_hash == event_hash)
                .values(status=status)
            )
            await session.commit()

    async def delete_processed_event(self, event_hash: str) -> None:
        async with self.session_factory() as session:
            result = await session.execute(
                select(ProcessedEvent).where(ProcessedEvent.event_hash == event_hash)
            )
            event = result.scalar_one_or_none()
            if event:
                await session.delete(event)
                await session.commit()

    async def save_prospect_state(self, state: Any) -> None:
        prospect_id_str = state.get("prospect_id")
        if not prospect_id_str:
            return
            
        prospect_id = uuid.UUID(prospect_id_str)
        status = state.get("overall_status", "PENDING")
        
        import json
        # Use stdlib json with default=str to handle UUIDs / datetimes without
        # pulling in FastAPI's encoder into the service layer.
        state_dict = json.loads(json.dumps(state, default=str))
        
        async with self.session_factory() as session:
            result = await session.execute(
                select(Prospect).where(Prospect.id == prospect_id)
            )
            prospect = result.scalar_one_or_none()
            
            if prospect:
                prospect.state_json = state_dict
                prospect.status = status
                prospect.workflow_thread_id = prospect_id_str
            else:
                display_id = f"PR-{str(prospect_id)[:6].upper()}"
                prospect = Prospect(
                    id=prospect_id,
                    display_id=display_id,
                    company_name=state.get("data", {}).get("company_name", "Unknown"),
                    status=status,
                    state_json=state_dict,
                    workflow_thread_id=prospect_id_str
                )
                session.add(prospect)
                
            await session.commit()

    async def load_prospect_state(self, prospect_id: str) -> Optional[Any]:
        try:
            pid = uuid.UUID(prospect_id)
        except ValueError:
            return None
            
        async with self.session_factory() as session:
            result = await session.execute(
                select(Prospect).where(Prospect.id == pid)
            )
            prospect = result.scalar_one_or_none()
            return prospect.state_json if prospect else None

    async def rollback_prospect_state(self, prospect_id: str) -> None:
        try:
            pid = uuid.UUID(prospect_id)
        except ValueError:
            return
            
        async with self.session_factory() as session:
            result = await session.execute(
                select(Prospect).where(Prospect.id == pid)
            )
            prospect = result.scalar_one_or_none()
            if prospect:
                prospect.status = "FAILED"
                await session.commit()

    async def save_emergency_state(self, state: Any) -> None:
        await self.save_prospect_state(state)

    async def list_prospects(self, filters: dict) -> List[ProspectSummary]:
        async with self.session_factory() as session:
            query = select(Prospect)
            
            status = filters.get("status")
            if status:
                query = query.where(Prospect.status == status)
                
            company_name = filters.get("company_name")
            if company_name:
                query = query.where(Prospect.company_name.ilike(f"%{company_name}%"))
                
            limit = filters.get("limit", 100)
            offset = filters.get("offset", 0)
            
            query = query.limit(limit).offset(offset)
            
            result = await session.execute(query)
            prospects = result.scalars().all()
            
            return [
                ProspectSummary(
                    id=p.id,
                    display_id=p.display_id,
                    company_name=p.company_name,
                    status=p.status,
                    updated_at=p.updated_at
                ) for p in prospects
            ]

    async def get_prospect(self, prospect_id: str) -> Optional[Prospect]:
        try:
            pid = uuid.UUID(prospect_id)
        except ValueError:
            return None
            
        async with self.session_factory() as session:
            result = await session.execute(
                select(Prospect).where(Prospect.id == pid)
            )
            return result.scalar_one_or_none()

    async def update_prospect_status(self, prospect_id: str, status: str) -> None:
        try:
            pid = uuid.UUID(prospect_id)
        except ValueError:
            return
            
        async with self.session_factory() as session:
            result = await session.execute(
                select(Prospect).where(Prospect.id == pid)
            )
            prospect = result.scalar_one_or_none()
            if prospect:
                prospect.status = status
                await session.commit()

    async def create_hitl_request(self, prospect_id: str, summary: str) -> uuid.UUID:
        try:
            pid = uuid.UUID(prospect_id)
        except ValueError:
            raise ValueError("Invalid prospect ID")
            
        async with self.session_factory() as session:
            display_id = f"HITL-{str(pid)[:6].upper()}"
            hitl = HITLRequest(
                prospect_id=pid,
                display_id=display_id,
                summary=summary
            )
            session.add(hitl)
            
            result = await session.execute(
                select(Prospect).where(Prospect.id == pid)
            )
            prospect = result.scalar_one_or_none()
            if prospect:
                prospect.status = "PENDING_HUMAN"
                
            await session.commit()
            return hitl.id

    async def get_pending_hitl_requests(self) -> List[HITLRequest]:
        async with self.session_factory() as session:
            result = await session.execute(
                select(HITLRequest).where(HITLRequest.decision == None)
            )
            return list(result.scalars().all())

    async def resolve_hitl_request(self, request_id: uuid.UUID, decision: str, corrections: Optional[dict]) -> None:
        import datetime
        
        async with self.session_factory() as session:
            result = await session.execute(
                select(HITLRequest).where(HITLRequest.id == request_id)
            )
            hitl = result.scalar_one_or_none()
            if hitl:
                hitl.decision = decision
                hitl.corrections = corrections
                hitl.resolved_at = get_utc_now()
                await session.commit()
