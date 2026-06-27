# Project Tracker – Agentic SaaS Platform for B2B Open Source SaaS Customer Discovery

## Project Overview
- **Goal**: Build a reusable Agentic AI Platform that orchestrates specialised agents to identify and qualify B2B prospects from open source SaaS companies.
- **Use Case**: Monitor web triggers, identify ICP companies, enrich data, find decision-makers, enrich contacts, generate summary, and get HITL approval.
- **Current Architecture Status**: Backend API via FastAPI, SQLite Database, and LangGraph workflow. The LangGraph nodes currently consolidate all agent logic into a unified `nodes.py` for rapid iteration.

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

## Phase 2.5 – Agent Layer Refactoring (COMPLETED)

- [x] Split `nodes.py` into individual agent modules under `src/agent/agents/`.
- [x] Injected dependencies (`toolbox`, `memory`) into all agent functions.
- [x] Added `config` field to `GraphState` to pre‑load ICP/persona/thresholds.
- [x] Modified `WorkflowService` to attach configuration to state before graph execution.
- [x] Removed all direct database imports from agent modules.
- [x] Updated `graph.py` to use `functools.partial` for dependency injection.
- [x] Deleted `src/agent/nodes.py`.
- [x] Verified graph compiles and runs without errors.

## Pending for Phase-3 (Frontend & Deployment)
1. **Frontend UI**:
   - Dashboard for configuring rules, monitoring triggers, and resolving HITL requests.
2. **Deployment Readiness**:
   - Migrate SQLite to PostgreSQL.
   - Containerize with Docker.

## Data Flow & State Structure
- **State Bus (`GraphState`)**: Uses `Annotated` reducers to merge `data` dictionaries and `validation_notes` lists. Contains `prospect_id`, `confidence_score`, `has_conflict`, etc.
- **Orchestration**: `graph.py` defines the state machine with conditional routing logic (e.g., `route_post_validation`, `route_post_hitl`).

## Decisions & Trade-offs
- Used SQLite for hackathon speed; will be replaced.
- Consolidated agents into `nodes.py` for rapid prototyping (Phase 1 & 2), maximizing iteration speed.
- Utilized inline LangGraph `interrupt()` for HITL functionality, allowing graceful pause/resume of the state machine.

## Key Files & Structure
- `src/models/` – SQLAlchemy schemas (`database.py`, `schemas.py`).
- `src/services/` – Business logic and database interactions.
- `src/api/routes/` – FastAPI endpoints.
- `src/agent/` – LangGraph core orchestration (`graph.py`), agents (`nodes.py`), state (`state.py`), tools (`utils.py`).

## Next Actions for Next Session
1. **Setup Frontend Scaffold**: Begin React/Next.js dashboard for HITL review.
2. **Test E2E Flow**: Verify the entire trigger -> enrich -> hitl -> complete cycle.

---
*Last updated: June 27, 2026*
