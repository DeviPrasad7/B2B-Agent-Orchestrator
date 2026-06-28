"""
TriggerMonitor – background polling loop for external event sources.

Outbox pattern (Fix 7):
  mark_event_processed writes status="processing" first.
  Only after WorkflowService.submit_prospect succeeds is the status
  updated to "completed". If the process crashes between the two writes,
  the event row stays at "processing" and a cleanup job (or the next poll
  cycle, see _cleanup_orphaned_events) can retry it.
"""

import asyncio
from core.logging import logger
import uuid
from sqlalchemy import select, update
from models.database import async_session, TriggerSource, ProcessedEvent
from services.memory_service import MemoryService
from services.workflow_service import WorkflowService
from agent.state import GraphState
from agent.utils import Toolbox
from services.api_providers import APIProviderFactory

class TriggerMonitor:
    def __init__(self, toolbox: Toolbox, workflow_service: WorkflowService):
        self.toolbox = toolbox
        self.workflow_service = workflow_service
        self.provider_factory = APIProviderFactory()
        self._running = False
        self._task = None
        self._last_polled = {} # source_id (str) -> timestamp (float)

    def start(self) -> None:
        if self._running:
            logger.warning("TriggerMonitor is already running.")
            return
        self._running = True
        self._task = asyncio.create_task(self._poll_loop())
        logger.info("TriggerMonitor started.")

    def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
        logger.info("TriggerMonitor stopped.")

    async def _poll_loop(self) -> None:
        while self._running:
            try:
                await self._cleanup_orphaned_events()
                await self.poll_sources()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Error in trigger monitor loop", error=str(e))

            await asyncio.sleep(60)

    async def _cleanup_orphaned_events(self) -> None:
        """Pick up events that were marked 'processing' but never completed.

        This happens if the process crashes between mark_event_processed and
        submit_prospect. We delete these rows so the next poll cycle retries.
        """
        import datetime
        # SQLAlchemy DateTime is naive by default, so we must use a naive datetime
        cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=5)
        async with async_session() as session:
            result = await session.execute(
                select(ProcessedEvent).where(
                    ProcessedEvent.status == "processing",
                    ProcessedEvent.processed_at < cutoff,
                )
            )
            orphans = result.scalars().all()
            for orphan in orphans:
                await session.delete(orphan)
            if orphans:
                await session.commit()
                logger.warning("Cleaned up orphaned processing events", count=len(orphans))

    async def poll_sources(self) -> None:
        import time
        current_time = time.time()
        
        # Fetch enabled sources in a short-lived session
        async with async_session() as session:
            result = await session.execute(
                select(TriggerSource).where(TriggerSource.enabled == True)
            )
            sources = result.scalars().all()

        # MemoryService expects a session *factory* (callable), not an open session.
        memory_service = MemoryService(async_session)

        for source in sources:
            source_id = str(source.id)
            last_polled = self._last_polled.get(source_id, 0)
            
            # Respect the configured polling interval
            if current_time - last_polled < source.interval_seconds:
                continue
                
            self._last_polled[source_id] = current_time

            # Global safety sleep: Ensure we never hit burst rate limits (> 5 req/sec) 
            # across our various API providers (News API, GitHub).
            await asyncio.sleep(0.5)
            
            try:
                entries = []
                provider = self.provider_factory.get_provider(source.type)
                if provider:
                    config = source.config or {}
                    # Add URL to config if present for generic providers
                    if source.url:
                        config["url"] = source.url
                    entries = await provider.fetch_entries(config)
                elif source.type == "rss":
                    # Keep RSS in toolbox for now unless we migrate it to a provider too
                    entries = await self.toolbox.fetch_rss_entries(source.url)
                elif source.type == "job_board":
                    company = source.config.get("company", "") if source.config else ""
                    entries = await self.toolbox.fetch_jobs(company)
                else:
                    logger.warning(f"Unsupported trigger source type: {source.type}")
                    continue

                for entry in entries:
                    event_hash = f"{source.type}_{entry.get('link', entry.get('title'))}"

                    if await memory_service.has_event_been_processed(event_hash):
                        continue

                    prospect_id = str(uuid.uuid4())

                    # ── Outbox step 1: mark as "processing" BEFORE submit ──────
                    # If we crash here, cleanup job will retry on next cycle.
                    inserted = await memory_service.mark_event_processed(
                        event_hash, prospect_id, status="processing"
                    )
                    if not inserted:
                        # Another worker just processed this event
                        continue

                    # Extract company name robustly (up to first 3 words)
                    raw_title = entry.get("title", "")
                    company_name = (
                        " ".join(raw_title.split(" ")[:3])
                        if source.type != "job_board"
                        else "Unknown"
                    )

                    state: GraphState = {
                        "prospect_id": prospect_id,
                        "current_trigger_event": entry.get("title", "Unknown Event"),
                        "data": {
                            "company_name": company_name,
                            "website_url": None,
                            "trigger_source": source.type,
                            "raw_event": entry,
                        },
                        "validation_notes": [],
                        "confidence_score": 0.0,
                        "overall_status": "PENDING",
                        "human_override_payload": None,
                        "executed_agents": [],
                        "errors": [],
                        "has_conflict": False,
                        "tech_detection_status": "PENDING",
                    }

                    try:
                        await memory_service.save_prospect_state(state)
                        await self.workflow_service.submit_prospect(state, prospect_id)

                        await memory_service.update_event_status(event_hash, "completed")

                        # Aggressive throttle to protect free-tier LLM rate limits
                        # Staggers pipeline executions heavily
                        await asyncio.sleep(15.0)

                        logger.info(
                            "Submitted new prospect from trigger",
                            source=source.type,
                            prospect_id=prospect_id,
                        )
                    except Exception as submit_err:
                        # Submission failed – delete the "processing" record so
                        # the cleanup job picks it up on the next cycle.
                        await memory_service.delete_processed_event(event_hash)
                        logger.error(
                            "Failed to submit prospect, event will be retried",
                            event_hash=event_hash,
                            error=str(submit_err),
                        )

            except Exception as e:
                logger.error("Error polling source", source_id=str(source.id), error=str(e))
