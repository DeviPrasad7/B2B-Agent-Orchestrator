# Project Tracker – Agentic SaaS Platform for B2B Open Source SaaS Customer Discovery

## Project Overview & Problem Statement
**Goal**: Design and build a reusable Agentic AI Platform that enables users to create, orchestrate, and deploy intelligent AI agents. The platform must be demonstrated by solving a real-world B2B customer discovery and prospect intelligence use case (identifying ICP Open Source SaaS companies).

**Core Challenge Requirements:**
1. **Dynamic Planner-Based Orchestration**: The orchestrator must not be a hard-coded DAG, but dynamically decide agent invocation based on state/input.
2. **Reusable Agent & Tool Architecture**: Agents and tools must adhere to standardized contracts for easy swapping/upgrading.
3. **Shared Contextual Memory**: A centralized, persistent memory layer to retain context across interactions, prevent redundant work, and support historical references.
4. **End-to-End Workflow**:
   - Monitor web/market sources for configurable triggers.
   - Apply editable ICP criteria to filter companies.
   - Validate and enrich firmographics.
   - Identify decision-makers via configurable target personas.
   - Enrich contacts (email, phone, LinkedIn).
   - Generate an actionable summary with recommended next actions.
   - **HITL (Human-in-the-Loop) Approval Gate**: Pause for explicit user approval before finalizing recommendations.
5. **Configurability & Extensibility**: User-editable business rules (ICP, thresholds, personas). Pluggable framework for adding new workflows/agents without altering core orchestration.
6. **User Experience**: Intuitive UI (web/CLI/desktop) for configuring rules, monitoring progress, and handling HITL requests.
7. **Deliverables**: 5-minute Demo, 5-minute Architecture Walkthrough, GitHub Repository.

## Current Architecture & Codebase Status (Deep Analysis)
- **Frameworks**: FastAPI (Backend API), LangGraph (Workflow Orchestration), SQLAlchemy (Database ORM), Streamlit (Frontend UI).
- **Database**: PostgreSQL is successfully used for production data and LangGraph checkpointer memory (`AsyncPostgresSaver`).
- **State Management**: Uses `GraphState` (TypedDict) with `Annotated` reducers. 
- **Orchestration Engine**: Implemented via `graph.py`. Successfully uses `DynamicPlannerNode` to dynamically route and select the next agent based on the LLM's decision rather than hard-coded conditional paths.
- **Agent Architecture**: Agents are modularized in `src/agent/agents/` and use a `@register_agent` decorator for open/closed principle extensibility. Dependencies are injected via `functools.partial`.
- **Services**: 
  - `ConfigService`: CRUD for ICP, personas.
  - `MemoryService`: DB-backed memory store.
  - `WorkflowService`: Wraps LangGraph invocation.
  - `HITLService`: Manages Human-In-The-Loop requests securely.
- **API**: FastAPI providing endpoints `/api/config`, `/api/prospects`, `/api/hitl`, `/api/triggers`.
- **Deployment**: `Dockerfile` is present and correctly configured with `entrypoint.sh` for production-grade `uvicorn` deployment.

## Fundamentals (Must-Have Requirements) Checklist
- [x] **Specialised Agent Pool**: monitor, score, tech_stack, enricher, competitor, validator, contact_finder, summarizer.
- [x] **Shared Contextual Memory**: Implemented via `MemoryService` and LangGraph Checkpointer.
- [x] **Configurable Trigger Monitoring**: Implemented in `monitor.py` and `trigger_monitor.py`.
- [x] **ICP Identification**: `score_node` applies config.
- [x] **Validation & Enrichment**: `enricher_node` and `cross_validator_node`.
- [x] **Persona-Based Decision-Maker Discovery**: `persona_matcher_node` and `contact_finder_node`.
- [x] **Actionable Summary Generation**: `summarizer_node`.
- [x] **HITL Approval Gate**: Integrated via `interrupt()` in `hitl_gateway_node`.
- [x] **User-Editable Business Rules**: Via ConfigService API.
- [x] **Pluggable Agent Framework**: Agents are decoupled via DI.
- [x] **Reusable Agent/Tool Interface**: `Toolbox` acts as a facade and correctly uses Dependency Inversion via protocol interfaces.
- [x] **Agentic Orchestration Engine**: A `DynamicPlannerNode` drives routing using an LLM to select the next agent based on context.
- [x] **Intuitive UI**: Streamlit application built and fully functional (`frontend/app.py`).
- [x] **GCP Production Readiness**: SQLite migrated to PostgreSQL in production, Dockerfile uses Uvicorn single worker.

---
*Last updated: June 28, 2026*
