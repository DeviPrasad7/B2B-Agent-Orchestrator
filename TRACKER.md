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
- **Frameworks**: FastAPI (Backend API), LangGraph (Workflow Orchestration), SQLAlchemy (Database ORM).
- **Database**: Currently using SQLite (`app.db` for app state, `checkpoints.db` for LangGraph memory). **[BLOCKER FOR GCP]** Cloud Run requires stateless architecture; SQLite will cause data loss on container restarts. Must migrate to PostgreSQL (e.g., Supabase/Neon) or Firestore.
- **State Management**: Uses `GraphState` (TypedDict) with `Annotated` reducers. LangGraph checkpointer `AsyncSqliteSaver` is active.
- **Orchestration Engine**: Implemented via `graph.py`. Currently uses a static StateGraph with conditional edges. To fully satisfy the "Dynamic Planner" requirement, the routing logic needs an LLM-driven planning agent rather than hard-coded conditional paths.
- **Agent Architecture**: Monolithic `nodes.py` was successfully split into individual files (`src/agent/agents/`). Dependencies are injected via `functools.partial`.
- **Services**: 
  - `ConfigService`: CRUD for ICP, personas.
  - `MemoryService`: DB-backed memory store. *BUG FOUND*: `hitl_service.py` incorrectly instantiates `MemoryService` with an active session rather than a session factory.
  - `WorkflowService`: Wraps LangGraph invocation.
  - `HITLService`: Manages Human-In-The-Loop requests.
- **API**: FastAPI providing endpoints `/api/config`, `/api/prospects`, `/api/hitl`, `/api/triggers`.
- **Deployment**: `Dockerfile` is present but uses `python app.py` with `reload=True`. Needs production-grade `uvicorn` configuration. `docker-compose.yml` mounts local volumes.

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
- [x] **Pluggable Agent Framework**: Agents are decoupled via DI, but `graph.py` requires manual edge wiring.
- [-] **Reusable Agent/Tool Interface**: `Toolbox` acts as a facade, but currently violates Dependency Inversion by instantiating concrete services internally.
- [-] **Agentic Orchestration Engine**: Basic LangGraph routing exists, but needs LLM planner to be truly "dynamic".
- [ ] **Intuitive UI**: Missing. Backend API only.
- [ ] **GCP Production Readiness**: Fails due to SQLite and dev-server configuration.

## Actionable Next Steps (See implementation_plan.md)
1. **GCP Free Tier Readiness**: Migrate SQLite to PostgreSQL/Firestore; update Dockerfile for production Uvicorn.
2. **SOLID Refactoring**: Fix Dependency Inversion in `Toolbox`; fix `MemoryService` initialization bug in `hitl_service.py`.
3. **Dynamic Planner Upgrade**: Introduce an LLM-driven Supervisor node in LangGraph to dynamically select agents, replacing hard-coded conditional edges.
4. **Frontend Implementation**: Build a lightweight React or Streamlit UI for the HITL dashboard.

---
*Last updated: June 27, 2026*
