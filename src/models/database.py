from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy import Column, String, JSON, DateTime, Integer, Boolean, ForeignKey, Uuid, Index, func
import uuid
from datetime import datetime, timezone

from core.settings import settings

db_url = settings.get_async_db_url()
engine_kwargs = {"echo": settings.APP_ENV == "development"}
if not db_url.startswith("sqlite"):
    engine_kwargs["pool_size"] = 5
    engine_kwargs["max_overflow"] = 10

engine = create_async_engine(db_url, **engine_kwargs)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

Base = declarative_base()

def get_utc_now():
    """Return a timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)

class Prospect(Base):
    __tablename__ = "prospects"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    display_id = Column(String, nullable=True, index=True)
    company_name = Column(String, nullable=False, index=True)
    website = Column(String, nullable=True)
    status = Column(String, nullable=False, default="PENDING", index=True)
    state_json = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=get_utc_now)
    updated_at = Column(DateTime(timezone=True), default=get_utc_now, onupdate=get_utc_now)
    workflow_thread_id = Column(String, nullable=True)

    # Relationships
    hitl_requests = relationship("HITLRequest", back_populates="prospect", lazy="noload")

class HITLRequest(Base):
    __tablename__ = "hitl_requests"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    display_id = Column(String, nullable=True, index=True)
    prospect_id = Column(Uuid, ForeignKey("prospects.id"), nullable=False)
    summary = Column(String, nullable=False)
    decision = Column(String, nullable=True, index=True)
    corrections = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    # Relationship – used by selectinload in HITLService.resolve_request
    prospect = relationship("Prospect", back_populates="hitl_requests", lazy="noload")

class CustomAgent(Base):
    __tablename__ = "custom_agents"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    name = Column(String, unique=True, index=True, nullable=False)
    description = Column(String, nullable=False)
    system_prompt = Column(String, nullable=False)
    allowed_tools = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Config(Base):
    __tablename__ = "config"

    key = Column(String, primary_key=True)
    value = Column(JSON, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=get_utc_now, onupdate=get_utc_now)

class TriggerSource(Base):
    __tablename__ = "trigger_sources"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    type = Column(String, nullable=False)
    url = Column(String, nullable=True)
    interval_seconds = Column(Integer, nullable=False, default=3600)
    enabled = Column(Boolean, nullable=False, default=True)
    config = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=get_utc_now)

class ProcessedEvent(Base):
    __tablename__ = "processed_events"

    event_hash = Column(String, primary_key=True)
    prospect_id = Column(String, nullable=False)
    # "processing" → set before workflow submission; "completed" → set after.
    # A background cleanup job can pick up stale "processing" rows (outbox pattern).
    status = Column(String, nullable=False, default="completed")
    processed_at = Column(DateTime(timezone=True), default=get_utc_now)


async def init_db():
    """Create all tables if they don't already exist.

    Safe to call on every startup – uses ``checkfirst=True`` internally
    (the default for ``create_all``).
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
