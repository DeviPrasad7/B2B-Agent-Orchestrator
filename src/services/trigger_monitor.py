import asyncio
import structlog
import uuid
import time
from sqlalchemy import select
from models.database import async_session, TriggerSource
from services.memory_service import MemoryService
from services.workflow_service import WorkflowService
from agent.state import GraphState
from agent.utils import Toolbox

logger = structlog.get_logger()
toolbox = Toolbox()

class TriggerMonitor:
    def __init__(self):
        self._running = False
        self._task = None

    def start(self):
        if self._running:
            logger.warning("TriggerMonitor is already running.")
            return
        self._running = True
        self._task = asyncio.create_task(self._poll_loop())
        logger.info("TriggerMonitor started.")

    def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
        logger.info("TriggerMonitor stopped.")

    async def _poll_loop(self):
        while self._running:
            try:
                await self.poll_sources()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Error in trigger monitor loop", error=str(e))
                
            # Sleep a bit before checking DB again
            await asyncio.sleep(60)

    async def poll_sources(self):
        # Fetch enabled sources
        async with async_session() as session:
            result = await session.execute(
                select(TriggerSource).where(TriggerSource.enabled == True)
            )
            sources = result.scalars().all()
            
        for source in sources:
            try:
                # Each source fetch uses its own session scope for memory service operations
                async with async_session() as session:
                    memory_service = MemoryService(session)
                    
                    entries = []
                    if source.type == "rss":
                        entries = await toolbox.fetch_rss_entries(source.url)
                    elif source.type == "news_api":
                        keywords = source.config.get("keywords", "") if source.config else ""
                        entries = await toolbox.fetch_news_api(keywords)
                    elif source.type == "job_board":
                        company = source.config.get("company", "") if source.config else ""
                        entries = await toolbox.fetch_jobs(company)
                    
                    for entry in entries:
                        # Create a unique hash for the event based on title or link
                        event_hash = f"{source.type}_{entry.get('link', entry.get('title'))}"
                        
                        if await memory_service.has_event_been_processed(event_hash):
                            continue
                            
                        prospect_id = str(uuid.uuid4())
                        
                        # Mark as processed immediately to prevent duplicate submissions
                        await memory_service.mark_event_processed(event_hash, prospect_id)
                        
                        # Extract company name via a mock logic (usually NLP/LLM)
                        company_name = entry.get("title", "").split(" ")[0] if source.type != "job_board" else "Unknown"
                        
                        state: GraphState = {
                            "prospect_id": prospect_id,
                            "current_trigger_event": entry.get("title", "Unknown Event"),
                            "data": {
                                "company_name": company_name,
                                "trigger_source": source.type,
                                "raw_event": entry
                            },
                            "validation_notes": [],
                            "confidence_score": 0.0,
                            "overall_status": "PENDING",
                            "human_override_payload": None,
                            "executed_agents": [],
                            "errors": [],
                            "has_conflict": False,
                            "tech_detection_status": "PENDING"
                        }
                        
                        await memory_service.save_prospect_state(state)
                        await WorkflowService.submit_prospect(state, prospect_id)
                        logger.info("Submitted new prospect from trigger", source=source.type, prospect_id=prospect_id)
                        
            except Exception as e:
                logger.error("Error polling source", source_id=str(source.id), error=str(e))
