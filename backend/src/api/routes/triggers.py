from fastapi import APIRouter, Depends, HTTPException, Request
from typing import List
from models.schemas import TriggerSourceSchema
from models.database import TriggerSource
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from api.dependencies import get_session
import uuid

router = APIRouter(prefix="/api/triggers", tags=["triggers"])

@router.get("/sources", response_model=List[TriggerSourceSchema])
async def list_sources(session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(TriggerSource))
    sources = result.scalars().all()
    return [
        TriggerSourceSchema(
            id=s.id,
            type=s.type,
            url=s.url,
            interval_seconds=s.interval_seconds,
            enabled=s.enabled,
            config=s.config,
            created_at=s.created_at
        ) for s in sources
    ]

@router.post("/sources", response_model=TriggerSourceSchema)
async def create_source(source_in: TriggerSourceSchema, session: AsyncSession = Depends(get_session)):
    new_source = TriggerSource(
        type=source_in.type,
        url=source_in.url,
        interval_seconds=source_in.interval_seconds,
        enabled=source_in.enabled,
        config=source_in.config
    )
    session.add(new_source)
    await session.commit()
    await session.refresh(new_source)
    
    return TriggerSourceSchema(
        id=new_source.id,
        type=new_source.type,
        url=new_source.url,
        interval_seconds=new_source.interval_seconds,
        enabled=new_source.enabled,
        config=new_source.config,
        created_at=new_source.created_at
    )

@router.delete("/sources/{source_id}")
async def delete_source(source_id: str, session: AsyncSession = Depends(get_session)):
    try:
        sid = uuid.UUID(source_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid source ID format")
        
    result = await session.execute(select(TriggerSource).where(TriggerSource.id == sid))
    source = result.scalar_one_or_none()
    
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
        
    await session.delete(source)
    await session.commit()
    return {"status": "success"}

@router.post("/start")
async def start_monitor(request: Request):
    # Access monitor via app.state to avoid circular import from api.main
    monitor = request.app.state.trigger_monitor
    monitor.start()
    return {"status": "success", "message": "TriggerMonitor started"}

@router.post("/stop")
async def stop_monitor(request: Request):
    # Access monitor via app.state to avoid circular import from api.main
    monitor = request.app.state.trigger_monitor
    monitor.stop()
    return {"status": "success", "message": "TriggerMonitor stopped"}

@router.get("/status")
async def get_monitor_status(request: Request):
    monitor = request.app.state.trigger_monitor
    return {"running": monitor._running}
