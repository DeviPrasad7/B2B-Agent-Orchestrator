from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, String, JSON, DateTime, Integer, Boolean, ForeignKey, Uuid
import uuid
from datetime import datetime, timezone

from core.settings import settings

engine = create_async_engine(
    settings.get_async_db_url(),
    echo=settings.APP_ENV == "development",
    pool_size=5,
    max_overflow=10,
)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

Base = declarative_base()

def get_utc_now():
    return datetime.now(timezone.utc)

class Prospect(Base):
    __tablename__ = "prospects"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    company_name = Column(String, nullable=False)
    website = Column(String, nullable=True)
    status = Column(String, nullable=False, default="PENDING")
    state_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=get_utc_now)
    updated_at = Column(DateTime, default=get_utc_now, onupdate=get_utc_now)
    workflow_thread_id = Column(String, nullable=True)

class HITLRequest(Base):
    __tablename__ = "hitl_requests"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    prospect_id = Column(Uuid, ForeignKey("prospects.id"), nullable=False)
    summary = Column(String, nullable=False)
    decision = Column(String, nullable=True)
    corrections = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=get_utc_now)
    resolved_at = Column(DateTime, nullable=True)

class Config(Base):
    __tablename__ = "config"

    key = Column(String, primary_key=True)
    value = Column(JSON, nullable=False)
    updated_at = Column(DateTime, default=get_utc_now, onupdate=get_utc_now)

class TriggerSource(Base):
    __tablename__ = "trigger_sources"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    type = Column(String, nullable=False)
    url = Column(String, nullable=True)
    interval_seconds = Column(Integer, nullable=False, default=3600)
    enabled = Column(Boolean, nullable=False, default=True)
    config = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=get_utc_now)

class ProcessedEvent(Base):
    __tablename__ = "processed_events"

    event_hash = Column(String, primary_key=True)
    prospect_id = Column(String, nullable=False)
    processed_at = Column(DateTime, default=get_utc_now)


async def init_db():
    """Create all tables if they don't already exist.

    Safe to call on every startup – uses ``checkfirst=True`` internally
    (the default for ``create_all``).
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
