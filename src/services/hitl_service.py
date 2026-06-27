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
        return request_id

    async def resolve_request(
        self,
        request_id: str,
        decision: str,
        corrections: Optional[dict],
    ) -> None:
        """Resolve a HITL request and resume the associated workflow.

        All DB reads and the resolve write are executed inside a single session
        to avoid detached-instance errors. The workflow is resumed after the
        session commits.
        """
        try:
            rid = uuid.UUID(request_id)
        except ValueError:
            raise ValueError("Invalid request ID")

        from models.database import HITLRequest, Prospect
        import datetime

        workflow_thread_id: Optional[str] = None

        # ── Single session boundary: read + update in one transaction ─────────
        async with self.memory_service.session_factory() as session:
            # Eager-load the prospect so we can read workflow_thread_id
            # before the session closes (avoids DetachedInstanceError).
            result = await session.execute(
                select(HITLRequest)
                .where(HITLRequest.id == rid)
                .options(selectinload(HITLRequest.prospect))
            )
            hitl = result.scalar_one_or_none()
            if not hitl:
                raise ValueError("HITL request not found")

            # Update HITL record
            hitl.decision = decision
            hitl.corrections = corrections
            hitl.resolved_at = get_utc_now()

            # Update prospect status
            if hitl.prospect:
                workflow_thread_id = hitl.prospect.workflow_thread_id
                hitl.prospect.status = "APPROVED" if decision == "APPROVED" else "REJECTED"

            await session.commit()
        # ── Session closed; ORM objects are now detached ─────────────────────

        # Resume the LangGraph workflow outside the DB session so the commit
        # is durable before we trigger async graph execution.
        if workflow_thread_id:
            if self.workflow_service:
                await self.workflow_service.resume_with_hitl(workflow_thread_id, decision, corrections)
            else:
                raise RuntimeError("workflow_service is not configured on HITLService")
