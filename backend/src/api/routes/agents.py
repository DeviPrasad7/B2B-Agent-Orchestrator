from fastapi import APIRouter, Depends, HTTPException
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models.database import CustomAgent
from models.schemas import CustomAgentCreate, CustomAgentDetail
from api.dependencies import get_session
import uuid

router = APIRouter(prefix="/api/agents", tags=["agents"])


@router.get("", response_model=List[CustomAgentDetail])
async def list_agents(session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(CustomAgent))
    agents = result.scalars().all()
    return [
        CustomAgentDetail(
            id=a.id,
            name=a.name,
            description=a.description,
            system_prompt=a.system_prompt,
            allowed_tools=a.allowed_tools or [],
            created_at=a.created_at,
        )
        for a in agents
    ]


@router.post("", response_model=CustomAgentDetail)
async def create_agent(agent: CustomAgentCreate, session: AsyncSession = Depends(get_session)):
    new_agent = CustomAgent(
        name=agent.name,
        description=agent.description,
        system_prompt=agent.system_prompt,
        allowed_tools=agent.allowed_tools,
    )
    session.add(new_agent)
    try:
        await session.commit()
        await session.refresh(new_agent)
    except Exception:
        await session.rollback()
        raise HTTPException(status_code=400, detail=f"Agent '{agent.name}' already exists or DB constraint violated.")

    return CustomAgentDetail(
        id=new_agent.id,
        name=new_agent.name,
        description=new_agent.description,
        system_prompt=new_agent.system_prompt,
        allowed_tools=new_agent.allowed_tools or [],
        created_at=new_agent.created_at,
    )


@router.delete("/{agent_id}", status_code=204)
async def delete_agent(agent_id: str, session: AsyncSession = Depends(get_session)):
    try:
        aid = uuid.UUID(agent_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid agent ID format")

    result = await session.execute(select(CustomAgent).where(CustomAgent.id == aid))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    await session.delete(agent)
    await session.commit()
