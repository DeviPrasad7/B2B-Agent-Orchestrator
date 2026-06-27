"""
HITLService – manages Human-in-the-Loop request lifecycle.

Key design decisions:
- All DB operations in ``resolve_request`` are executed inside a **single**
  ``async with session_factory()`` block to prevent detached-ORM errors.
  SQLAlchemy's ``selectinload`` eager-loads the associated Prospect so we
  can read ``prospect.workflow_thread_id`` before the session closes.
- The workflow is resumed **after** the session closes so the DB commit is
  durable before we hand control back to LangGraph.
"""

import uuid
from typing import Optional
from sqlalchemy.orm import selectinload
from sqlalchemy import select
from services.memory_service import MemoryService
from services.workflow_service import WorkflowService
from models.database import get_utc_now


class HITLService:
    def __init__(self, memory_service: MemoryService):
        self.memory_service = memory_service
        self.workflow_service = None

    async def create_request(self, prospect_id: str, interrupt_data: dict) -> uuid.UUID:
        """Create a new HITL request record and mark the prospect as pending human review."""
        summary = interrupt_data.get("reason", "Manual review requested")
        request_id = await self.memory_service.create_hitl_request(prospect_id, summary)
        # Reflect the paused state in the Prospect row so the UI shows PENDING_HUMAN.
        await self.memory_service.update_prospect_status(prospect_id, "PENDING_HUMAN")
        return request_id

    async def resolve_request(
        self,
        request_id: str,
        decision: str,
        corrections: Optional[dict],
    ) -> None:
        """Resolve a HITL request and resume the associated workflow.

        DB operations are delegated to MemoryService.
        """
        try:
            rid = uuid.UUID(request_id)
        except ValueError:
            raise ValueError("Invalid request ID")

        workflow_thread_id = await self.memory_service.resolve_hitl_request_and_update_prospect(rid, decision, corrections)

        if workflow_thread_id:
            if self.workflow_service:
                await self.workflow_service.resume_with_hitl(workflow_thread_id, decision, corrections)
            else:
                raise RuntimeError("workflow_service is not configured on HITLService")
