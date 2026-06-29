from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
import uuid
from datetime import datetime

from models.database import Workflow
from api.dependencies import get_session

router = APIRouter(prefix="/api/workflows", tags=["workflows"])

class WorkflowCreate(BaseModel):
    name: str
    description: Optional[str] = None
    steps: Any

class WorkflowDetail(WorkflowCreate):
    id: uuid.UUID
    created_at: datetime

@router.get("", response_model=List[WorkflowDetail])
async def list_workflows(session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Workflow).order_by(Workflow.created_at.desc()))
    workflows = result.scalars().all()
    return [
        WorkflowDetail(
            id=w.id,
            name=w.name,
            description=w.description,
            steps=w.steps,
            created_at=w.created_at,
        )
        for w in workflows
    ]

@router.post("", response_model=WorkflowDetail)
async def create_workflow(workflow: WorkflowCreate, session: AsyncSession = Depends(get_session)):
    new_workflow = Workflow(
        name=workflow.name,
        description=workflow.description,
        steps=workflow.steps
    )
    session.add(new_workflow)
    try:
        await session.commit()
        await session.refresh(new_workflow)
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=400, detail=str(e))

    return WorkflowDetail(
        id=new_workflow.id,
        name=new_workflow.name,
        description=new_workflow.description,
        steps=new_workflow.steps,
        created_at=new_workflow.created_at,
    )

@router.delete("/{workflow_id}")
async def delete_workflow(workflow_id: str, session: AsyncSession = Depends(get_session)):
    try:
        wid = uuid.UUID(workflow_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid workflow ID")
        
    result = await session.execute(select(Workflow).where(Workflow.id == wid))
    workflow = result.scalar_one_or_none()
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
        
    await session.delete(workflow)
    await session.commit()
    return {"status": "success"}
