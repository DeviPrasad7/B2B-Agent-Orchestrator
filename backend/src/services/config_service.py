import yaml
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from models.database import Config
from models.schemas import ICPCriteria, PersonaDefinition, ThresholdConfig

class ConfigService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def _load_defaults(self):
        # Fallback hardcoded defaults in case file is missing
        default_data = {
            "icp": {
                "industries": ["Software"],
                "min_revenue": 1000000,
                "max_revenue": 50000000,
                "min_employees": 10,
                "max_employees": 500,
                "locations": ["North America"],
                "tech_stack": ["React"],
                "behaviors": ["Hiring developers"],
                "operator": "OR"
            },
            "persona": {
                "job_titles": ["CTO"],
                "seniority_levels": ["C-Level"],
                "functions": ["Engineering"],
                "exclude_titles": ["Recruiter"]
            },
            "thresholds": {
                "min_confidence_score": 50.0,
                "max_errors_allowed": 3,
                "hitl_confidence_threshold": 70.0,
                "auto_approve_threshold": 90.0
            }
        }
        
        # Resolve relative to the repo root regardless of CWD (works in Docker and locally).
        # File tree: backend/src/services/config_service.py → 3 parents up → repo root.
        default_file = Path(__file__).parents[2] / "default_icp.yaml"
        if default_file.exists():
            with open(default_file, "r") as f:
                loaded = yaml.safe_load(f)
                if loaded:
                    default_data.update(loaded)

        return default_data

    async def _get_config(self, key: str, schema_class, default_key: str):
        result = await self.session.execute(select(Config).where(Config.key == key))
        config = result.scalar_one_or_none()
        if config:
            return schema_class(**config.value)
        
        defaults = await self._load_defaults()
        default_value = defaults.get(default_key, {})
        
        # Save default to DB
        new_config = Config(key=key, value=default_value)
        self.session.add(new_config)
        await self.session.commit()
        return schema_class(**default_value)

    async def _update_config(self, key: str, value_dict: dict):
        result = await self.session.execute(select(Config).where(Config.key == key))
        config = result.scalar_one_or_none()
        if config:
            config.value = value_dict
        else:
            config = Config(key=key, value=value_dict)
            self.session.add(config)
        await self.session.commit()

    async def get_icp(self) -> ICPCriteria:
        return await self._get_config("icp", ICPCriteria, "icp")

    async def update_icp(self, criteria: ICPCriteria) -> None:
        await self._update_config("icp", criteria.model_dump())

    async def get_persona(self) -> PersonaDefinition:
        return await self._get_config("persona", PersonaDefinition, "persona")

    async def update_persona(self, persona: PersonaDefinition) -> None:
        await self._update_config("persona", persona.model_dump())

    async def get_thresholds(self) -> ThresholdConfig:
        return await self._get_config("thresholds", ThresholdConfig, "thresholds")

    async def update_thresholds(self, thresholds: ThresholdConfig) -> None:
        await self._update_config("thresholds", thresholds.model_dump())

    async def reset_to_defaults(self) -> None:
        await self.session.execute(delete(Config))
        await self.session.commit()
        # This will trigger a re-insertion of defaults into the DB
        await self._get_config("icp", ICPCriteria, "icp")
        await self._get_config("persona", PersonaDefinition, "persona")
        await self._get_config("thresholds", ThresholdConfig, "thresholds")
