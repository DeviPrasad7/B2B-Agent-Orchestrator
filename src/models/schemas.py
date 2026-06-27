from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from uuid import UUID

# Configuration Schemas
class ICPCriteria(BaseModel):
    industries: List[str]
    min_revenue: int
    max_revenue: int
    min_employees: int
    max_employees: int
    locations: List[str]
    tech_stack: List[str]
    behaviors: List[str]
    operator: str = "OR"

class PersonaDefinition(BaseModel):
    job_titles: List[str]
    seniority_levels: List[str]
    functions: List[str]
    exclude_titles: List[str] = []

class ThresholdConfig(BaseModel):
    min_confidence_score: float
    max_errors_allowed: int
    hitl_confidence_threshold: float
    auto_approve_threshold: float

# Prospect Schemas
class ProspectSummary(BaseModel):
    id: UUID
    display_id: Optional[str] = None
    company_name: str
    status: str
    updated_at: datetime

class ProspectDetail(BaseModel):
    id: UUID
    display_id: Optional[str] = None
    company_name: str
    website: Optional[str]
    status: str
    state_json: Optional[Dict[str, Any]]
    created_at: datetime
    updated_at: datetime
    workflow_thread_id: Optional[str]

# Note: ProspectState is defined in agent/state.py as GraphState,
# so we might map it directly to Dict[str, Any] in API, or use a Pydantic model
class HITLRequestDetail(BaseModel):
    id: UUID
    display_id: Optional[str] = None
    prospect_id: UUID
    summary: str
    decision: Optional[str] = None
    corrections: Optional[dict] = None
    created_at: datetime
    resolved_at: Optional[datetime] = None

class CustomAgentCreate(BaseModel):
    name: str
    description: str
    system_prompt: str
    allowed_tools: List[str] = []

class CustomAgentDetail(CustomAgentCreate):
    id: UUID
    created_at: datetime


class TriggerSourceSchema(BaseModel):
    id: Optional[UUID] = None
    type: str
    url: Optional[str] = None
    interval_seconds: int = 3600
    enabled: bool = True
    config: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
