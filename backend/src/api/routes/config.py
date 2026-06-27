from fastapi import APIRouter, Depends

from models.schemas import ICPCriteria, PersonaDefinition, ThresholdConfig
from services.config_service import ConfigService
from sqlalchemy.ext.asyncio import AsyncSession
from api.dependencies import get_session

router = APIRouter(prefix="/api/config", tags=["config"])


def get_config_service(session: AsyncSession = Depends(get_session)) -> ConfigService:
    return ConfigService(session)


@router.get("/icp", response_model=ICPCriteria)
async def get_icp(config_service: ConfigService = Depends(get_config_service)):
    return await config_service.get_icp()


@router.put("/icp")
async def update_icp(criteria: ICPCriteria, config_service: ConfigService = Depends(get_config_service)):
    await config_service.update_icp(criteria)
    return {"status": "success"}


@router.get("/persona", response_model=PersonaDefinition)
async def get_persona(config_service: ConfigService = Depends(get_config_service)):
    return await config_service.get_persona()


@router.put("/persona")
async def update_persona(persona: PersonaDefinition, config_service: ConfigService = Depends(get_config_service)):
    await config_service.update_persona(persona)
    return {"status": "success"}


@router.get("/thresholds", response_model=ThresholdConfig)
async def get_thresholds(config_service: ConfigService = Depends(get_config_service)):
    return await config_service.get_thresholds()


@router.put("/thresholds")
async def update_thresholds(thresholds: ThresholdConfig, config_service: ConfigService = Depends(get_config_service)):
    await config_service.update_thresholds(thresholds)
    return {"status": "success"}


@router.post("/reset")
async def reset_config(config_service: ConfigService = Depends(get_config_service)):
    await config_service.reset_to_defaults()
    return {"status": "success"}
