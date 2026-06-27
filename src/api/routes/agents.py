from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models.database import async_session, CustomAgent
from models.schemas import CustomAgentCreate, CustomAgentDetail
import uuid
from typing import List

router = APIRouter(prefix="/api/agents", tags=["agents"])

async def get_session():
    async with async_session() as session:
        yield session

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
            created_at=a.created_at
        ) for a in agents
    ]

@router.post("", response_model=CustomAgentDetail)
async def create_agent(agent: CustomAgentCreate, session: AsyncSession = Depends(get_session)):
    new_agent = CustomAgent(
        name=agent.name,
        description=agent.description,
        system_prompt=agent.system_prompt,
        allowed_tools=agent.allowed_tools
    )
    session.add(new_agent)
    try:
        await session.commit()
        await session.refresh(new_agent)
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=400, detail="Agent with this name might already exist")
        
    return CustomAgentDetail(
        id=new_agent.id,
        name=new_agent.name,
        description=new_agent.description,
        system_prompt=new_agent.system_prompt,
        allowed_tools=new_agent.allowed_tools or [],
        created_at=new_agent.created_at
    )
