# Project Tracker – Agentic SaaS Platform for B2B Open Source SaaS Customer Discovery

## Project Overview
- **Goal**: Build a reusable Agentic AI Platform that orchestrates specialised agents to identify and qualify B2B prospects from open source SaaS companies.
- **Use Case**: Monitor web triggers, identify ICP companies, enrich data, find decision-makers, enrich contacts, generate summary, and get HITL approval.
- **Current Architecture Status**: Backend API via FastAPI, SQLite Database, and LangGraph workflow. The LangGraph nodes currently exhibit high coupling and low cohesion (all agent logic consolidated in `nodes.py` referencing global utilities). 

## Fundamentals (Must-Have Requirements)
- [x] Agentic Orchestration Engine (Planner-based dynamic routing)
- [x] Specialised Agent Pool (monitor, score, tech stack, enricher, competitor, cross-validator, summarizer, HITL, output dispatcher)
- [x] Reusable Agent/Tool Interface (IAgent, IToolbox)
- [x] Shared Contextual Memory (initial in-memory, now migrating to DB)
- [x] Configurable Trigger Monitoring (phase-2)
- [x] ICP Identification (configurable)
- [x] Validation & Enrichment (partially done)
- [x] Persona-Based Decision-Maker Discovery (new agents pending)
- [x] Contact Enrichment (new agents pending)
- [x] Actionable Summary Generation (done)
- [x] HITL Approval Gate (integrated via interrupt)
- [x] User-Editable Business Rules (phase-1 config service)
- [x] Pluggable Agent Framework (done via IAgent)
- [ ] Intuitive UI (backend only – API provides)

## Current Status (End of Phase-2)
- **Database**: SQLite (`app.db`) with SQLAlchemy models: `Prospect`, `HITLRequest`, `Config`, `TriggerSource`, `ProcessedEvent`.
- **State Management**: LangGraph checkpointer uses `SqliteSaver` via `checkpoints.db`.
- **Workflow & Agents**: Implemented `GraphState` with parallel nodes (monitor/score -> tech_stack/enrich -> competitor/validator -> persona/contact -> summarizer -> HITL -> output). All nodes are currently implemented in `src/agent/nodes.py`.
- **Services**: 
  - `ConfigService`: CRUD for ICP, personas.
  - `MemoryService`: DB-backed memory store.
  - `WorkflowService`: Wraps LangGraph invocation asynchronously.
  - `HITLService`: Manages Human-In-The-Loop requests.
- **API**: FastAPI providing `/api/config`, `/api/prospects`, `/api/hitl`, `/api/triggers`.

## Pending for Phase-3 (Refactoring & Frontend)
1. **Architectural Refactoring (Address Technical Debt)**:
   - **Fix Low Cohesion / High Coupling**: Split `nodes.py` into separate domain-specific agent classes adhering to SOLID principles.
   - **Dependency Injection**: Remove global instantiation of `Toolbox` and `MemoryStore` in `nodes.py`. Pass them explicitly via state or a context manager to decouple testing.
2. **Frontend UI**:
   - Dashboard for configuring rules, monitoring triggers, and resolving HITL requests.
3. **Deployment Readiness**:
   - Migrate SQLite to PostgreSQL.
   - Containerize with Docker.

## Data Flow & State Structure
- **State Bus (`GraphState`)**: Uses `Annotated` reducers to merge `data` dictionaries and `validation_notes` lists. Contains `prospect_id`, `confidence_score`, `has_conflict`, etc.
- **Orchestration**: `graph.py` defines the state machine with conditional routing logic (e.g., `route_post_validation`, `route_post_hitl`).

## Decisions & Trade-offs
- Used SQLite for hackathon speed; will be replaced.
- Consolidated agents into `nodes.py` for rapid prototyping (Phase 1 & 2), accepting the temporary technical debt of low cohesion.
- Utilized inline LangGraph `interrupt()` for HITL functionality, allowing graceful pause/resume of the state machine.

## Key Files & Structure
- `src/models/` – SQLAlchemy schemas (`database.py`, `schemas.py`).
- `src/services/` – Business logic and database interactions.
- `src/api/routes/` – FastAPI endpoints.
- `src/agent/` – LangGraph core orchestration (`graph.py`), agents (`nodes.py`), state (`state.py`), tools (`utils.py`).

## Next Actions for Next Session
1. **Refactor `nodes.py`**: Break out individual agents into a `src/agent/agents/` module and introduce proper interfaces to enforce SOLID principles.
2. **Setup Frontend Scaffold**: Begin React/Next.js dashboard for HITL review.
3. **Test E2E Flow**: Verify the entire trigger -> enrich -> hitl -> complete cycle.

---
*Last updated: June 27, 2026*
