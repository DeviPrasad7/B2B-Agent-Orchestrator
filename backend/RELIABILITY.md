<h1 align="center">Agentic Reliability Engineering</h1>

<p align="center">
  <strong>A deep-dive into the reliability engineering practices that make the ICP Agent platform production-grade -- covering circuit breakers, retry strategies, fault isolation, outbox-pattern event processing, graceful degradation, multi-provider LLM failover, heuristic validation, and stochastic reliability models.</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Circuit_Breaker-3_State_FSM-E91E63?style=for-the-badge" alt="Circuit Breaker">
  <img src="https://img.shields.io/badge/Fault_Isolation-SafeAgentWrapper-9C27B0?style=for-the-badge" alt="Fault Isolation">
  <img src="https://img.shields.io/badge/Outbox_Pattern-Exactly_Once-FF6F00?style=for-the-badge" alt="Outbox">
  <img src="https://img.shields.io/badge/LLM_Failover-Dual_Pool-2196F3?style=for-the-badge" alt="Failover">
  <img src="https://img.shields.io/badge/Graceful_Degradation-Always_On-4CAF50?style=for-the-badge" alt="Degradation">
  <br>
  <img src="https://img.shields.io/badge/Heuristics-State_Scoring-FF5722?style=for-the-badge" alt="Heuristics">
  <img src="https://img.shields.io/badge/Math-Stochastic_Modeling-00BCD4?style=for-the-badge" alt="Math">
  <img src="https://img.shields.io/badge/Regex-Sanitization_Pipelines-795548?style=for-the-badge" alt="Regex">
</p>

---

## Table of Contents

- [Reliability Architecture Overview](#reliability-architecture-overview)
- [Circuit Breaker Pattern](#circuit-breaker-pattern)
- [Fault Isolation via SafeAgentWrapper](#fault-isolation-via-safeagentwrapper)
- [Outbox Pattern for Event Processing](#outbox-pattern-for-event-processing)
- [LLM Multi-Provider Failover](#llm-multi-provider-failover)
- [Retry Strategies and Error Budgets](#retry-strategies-and-error-budgets)
- [Heuristic Functions & Mathematical Models](#heuristic-functions--mathematical-models)
- [Graceful Degradation Hierarchy](#graceful-degradation-hierarchy)
- [State Durability and Crash Recovery](#state-durability-and-crash-recovery)
- [Rate Limiting and Throttling](#rate-limiting-and-throttling)
- [Observability and Monitoring](#observability-and-monitoring)
- [Failure Scenario Analysis](#failure-scenario-analysis)

---

## Reliability Architecture Overview

The ICP Agent platform implements a **defense-in-depth reliability model** where every layer of the stack has independent failure handling:

```mermaid
graph TB
    subgraph L1["Layer 1: API Gateway"]
        CORS["CORS Protection"]
        HEALTH["Health Check Endpoint"]
        VALIDATION["Pydantic Schema Validation"]
    end

    subgraph L2["Layer 2: Service Isolation"]
        CB["Circuit Breaker<br/>3-State FSM"]
        RETRY["Per-Agent Retry Tracking"]
        FALLBACK["Deterministic Fallback Routing"]
    end

    subgraph L3["Layer 3: Agent Fault Isolation"]
        SAW["SafeAgentWrapper<br/>Exception Boundary"]
        TRACE["Execution Trace Recording"]
        TIMEOUT["Agent-Level Timeout Protection"]
    end

    subgraph L4["Layer 4: Data Durability"]
        OUTBOX["Outbox Pattern<br/>Exactly-Once Semantics"]
        CHECKPOINT["LangGraph Checkpointing<br/>PostgreSQL-backed"]
        STATE["Intermediate State Persistence"]
    end

    subgraph L5["Layer 5: LLM Resilience"]
        POOL["Dual Provider Pools<br/>Groq + Gemini"]
        ROBIN["Round-Robin Rotation"]
        LIMIT["Global Rate Limiting"]
        GRACEFUL["Fallback Responses"]
    end

    L1 --> L2
    L2 --> L3
    L3 --> L4
    L4 --> L5
```

The guiding principle is: **the system should always make forward progress, even when individual components fail.** An LLM timeout doesn't crash the pipeline -- it falls back to the next model. An agent exception doesn't terminate the workflow -- it's caught by the wrapper and recorded in the state. An event processing failure doesn't lose the event -- it's retried on the next poll cycle.

---

## Circuit Breaker Pattern

### Three-State Finite State Machine

The `CircuitBreaker` class implements the classic three-state FSM to protect external service calls:

```mermaid
stateDiagram-v2
    [*] --> CLOSED: Initial State

    CLOSED --> CLOSED: Success (reset counter)
    CLOSED --> OPEN: Failure Count >= Threshold

    OPEN --> OPEN: Within Reset Timeout
    OPEN --> HALF_OPEN: Reset Timeout Expired

    HALF_OPEN --> CLOSED: Probe Call Succeeds
    HALF_OPEN --> OPEN: Probe Call Fails
```

### State Transition Rules

| Current State | Event | Next State | Action |
|:---|:---|:---|:---|
| `CLOSED` | Success | `CLOSED` | Reset failure counter to 0 |
| `CLOSED` | Failure (count < threshold) | `CLOSED` | Increment failure counter |
| `CLOSED` | Failure (count >= threshold) | `OPEN` | Trip breaker, record timestamp |
| `OPEN` | Any call (within timeout) | `OPEN` | Reject immediately (fast-fail) |
| `OPEN` | Timeout expired | `HALF_OPEN` | Allow a single probe call |
| `HALF_OPEN` | Probe success | `CLOSED` | Reset counter, resume normal operation |
| `HALF_OPEN` | Probe failure | `OPEN` | Re-trip breaker, reset timeout |

### Configuration

| Parameter | Default | Purpose |
|:---|:---:|:---|
| `failure_threshold` | 3 | Number of consecutive failures before tripping |
| `reset_timeout_sec` | 30 | Seconds to wait before allowing a probe call |

### Per-Service State Tracking

The circuit breaker tracks state independently for each external service:

```mermaid
graph LR
    CB["CircuitBreaker Instance"]
    
    CB --> S1["openai_api: CLOSED"]
    CB --> S2["tavily_api: HALF_OPEN"]
    CB --> S3["github_api: OPEN"]
    CB --> S4["linkedin_api: CLOSED"]
```

This means a failure in the GitHub API won't block calls to Tavily or LinkedIn. Each service degrades independently.

### Integration Point

The circuit breaker is integrated into the `Toolbox` facade, which is the single point of contact between agents and external services:

```python
class Toolbox:
    def __init__(self, llm_service, scraping_service, enrichment_service):
        self.circuit_breaker = CircuitBreaker()
        # ...
```

### Production Scaling Note

The current implementation is in-memory, suitable for single-worker deployments. The codebase includes an explicit note for production scaling:

> *"In a multi-worker cluster, replace CircuitBreaker with a Redis-backed implementation so all workers share failure counts."*

---

## Fault Isolation via SafeAgentWrapper

### The SafeAgentWrapper Pattern

Every agent in the LangGraph workflow is wrapped in a `SafeAgentWrapper` that provides a **hard exception boundary**:

```mermaid
graph TB
    subgraph Wrapper["SafeAgentWrapper"]
        TRY["try:"]
        EXEC["agent.__call__(state)"]
        TRACE["Record execution trace"]
        
        CATCH["except:"]
        CHECK["Is GraphInterrupt?"]
        
        subgraph Yes["Control Flow Exception"]
            RERAISE["Re-raise (let LangGraph handle)"]
        end
        
        subgraph No["Application Exception"]
            LOG["Log error via structlog"]
            RETRY["Increment retry_counts"]
            SAFE["Return safe error dict"]
        end
    end

    TRY --> EXEC
    EXEC -->|Success| TRACE
    EXEC -->|Exception| CATCH
    CATCH --> CHECK
    CHECK -->|Yes| RERAISE
    CHECK -->|No| LOG
    LOG --> RETRY
    RETRY --> SAFE
```

### What the Wrapper Provides

| Capability | Description |
|:---|:---|
| **Exception Isolation** | Unhandled exceptions in any agent are caught and converted to safe state updates, preventing workflow crashes |
| **Execution Tracing** | Every agent execution records its name, timestamp, duration, thoughts, and updates in the `execution_trace` list |
| **Retry Tracking** | The wrapper maintains per-agent retry counts in the graph state, enabling the planner to make informed retry/skip decisions |
| **Control Flow Preservation** | LangGraph control flow exceptions (`GraphInterrupt`, `NodeInterrupt`) are explicitly re-raised, ensuring HITL interrupts work correctly |
| **Agent Identity** | The wrapper sets `last_agent` in the state, allowing the planner to know which agent just executed |

### Execution Trace Record

Each agent execution produces a trace record:

```python
trace_record = {
    "agent": "enricher_node",
    "timestamp": 1719648000.0,
    "duration_seconds": 2.3,
    "recent_thoughts": ["Extracted firmographic data for Acme Corp"],
    "updates": {"data": {"firmographics": {...}}}
}
```

This creates a complete audit trail of the pipeline execution, invaluable for debugging and observability.

---

## Outbox Pattern for Event Processing

### The Problem

When processing external events (RSS feeds, GitHub webhooks, News API articles), the system must guarantee that each event is processed **exactly once**, even in the face of process crashes.

### The Solution: Two-Phase Outbox

```mermaid
sequenceDiagram
    participant TM as TriggerMonitor
    participant DB as PostgreSQL
    participant WS as WorkflowService

    TM->>DB: INSERT processed_events (status='processing')
    Note over TM,DB: PHASE 1: Intent recorded

    TM->>WS: submit_prospect(state)
    
    alt Submission succeeds
        TM->>DB: UPDATE processed_events SET status='completed'
        Note over TM,DB: PHASE 2: Confirmation recorded
    else Process crashes before Phase 2
        Note over DB: Row stays at 'processing'
        Note over TM: Next poll cycle...
        TM->>TM: _cleanup_orphaned_events()
        TM->>DB: DELETE WHERE status='processing' AND age > 5min
        Note over TM: Event will be retried
    else Submission fails (exception)
        TM->>DB: DELETE processed_events WHERE hash=event_hash
        Note over TM: Event will be retried on next cycle
    end
```

### Orphan Cleanup

The `_cleanup_orphaned_events()` method runs at the start of every poll cycle:

```mermaid
graph TB
    START["Poll Cycle Start"]
    QUERY["SELECT FROM processed_events<br/>WHERE status='processing'<br/>AND age > 5 minutes"]
    FOUND{"Orphans Found?"}
    DELETE["DELETE orphaned rows"]
    CONTINUE["Continue to poll_sources()"]

    START --> QUERY
    QUERY --> FOUND
    FOUND -->|Yes| DELETE
    FOUND -->|No| CONTINUE
    DELETE --> CONTINUE
```

### Concurrency Protection

The `mark_event_processed()` method uses database-level `IntegrityError` handling:

```python
async def mark_event_processed(self, event_hash: str, prospect_id: str, status: str) -> bool:
    try:
        event = ProcessedEvent(event_hash=event_hash, ...)
        session.add(event)
        await session.commit()
        return True
    except IntegrityError:
        await session.rollback()
        return False  # Another worker already claimed this event
```

If two workers attempt to process the same event simultaneously, only one will succeed -- the other will receive `False` and skip the event.

---

## LLM Multi-Provider Failover

### Dual-Pool Architecture

The `LLMService` maintains two independent model pools for maximum resilience:

```mermaid
graph TB
    subgraph Request["Incoming LLM Request"]
        REQ["generate_text(prompt, fallback)"]
    end

    subgraph Pool1["Groq Pool (Primary)"]
        G1["llama-3.3-70b-versatile"]
        G2["llama-3.1-8b-instant"]
        G3["openai/gpt-oss-120b"]
        G4["openai/gpt-oss-20b"]
    end

    subgraph Pool2["Gemini Pool (Secondary)"]
        M1["gemini-3.1-flash-lite"]
        M2["gemini-2.5-flash-lite"]
        M3["gemini-3.5-flash"]
        M4["gemini-2.5-flash"]
    end

    subgraph Fallback["Fallback"]
        FB["Return hardcoded fallback string"]
    end

    REQ --> Pool1
    Pool1 -->|All exhausted| Pool2
    Pool2 -->|All exhausted| Fallback
```

### Failover Cascade

```mermaid
sequenceDiagram
    participant C as Caller
    participant L as LLMService
    participant G as Groq Pool
    participant M as Gemini Pool

    C->>L: generate_text(prompt)
    
    L->>G: Try model 1 (llama-3.3-70b)
    G-->>L: RateLimitError
    L->>G: Try model 2 (llama-3.1-8b)
    G-->>L: RateLimitError
    L->>G: Try model 3 (gpt-oss-120b)
    G-->>L: RateLimitError
    L->>G: Try model 4 (gpt-oss-20b)
    G-->>L: RateLimitError
    
    Note over L: Groq pool exhausted, cascading to Gemini
    
    L->>M: Try model 1 (gemini-3.1-flash-lite)
    M-->>L: Success!
    L-->>C: Response text
```

### Key-Multiplication Strategy

Multiple API keys per provider create a multiplicative pool size:

```
Groq: 2 keys x 4 models = 8 model instances
Gemini: 5 keys x 4 models = 20 model instances
Total: 28 model instances in the failover chain
```

This means the system can absorb up to 27 consecutive failures before falling back to the hardcoded response.

### Round-Robin Rotation

Each successful or failed call rotates the model to the end of the pool, ensuring even load distribution and preventing a single failing model from being hammered repeatedly.

---

## Retry Strategies and Error Budgets

### Per-Agent Retry Tracking

Retry counts are tracked per-agent in the `GraphState`:

```python
retry_counts: Annotated[dict[str, int], add_dict]
```

The `SafeAgentWrapper` increments the count on failure:

```python
retry_counts = state.get("retry_counts", {})
current_retries = retry_counts.get(self.agent_name, 0)
return {
    "retry_counts": {self.agent_name: current_retries + 1}
}
```

### Simulate Failure Toggle

The `DynamicPlannerNode` includes a built-in failure simulation mode for testing:

```mermaid
graph TB
    SIM{"simulate_failure?"}
    RETRY{"retries < 2?"}
    FORCE["Force retry on last_agent"]
    NORMAL["Normal routing"]

    SIM -->|Yes| RETRY
    SIM -->|No| NORMAL
    RETRY -->|Yes| FORCE
    RETRY -->|No| NORMAL
```

This allows the system to be tested under failure conditions without actually breaking external services.

### Recursion Limit

The LangGraph workflow is compiled with `recursion_limit=100`, providing an absolute ceiling on the number of planner-agent cycles. This prevents infinite loops in pathological cases.

---

## Heuristic Functions & Mathematical Models

To elevate the system from a simple agent wrapper to a deterministic, production-grade software engine, we employ advanced heuristic scoring, stochastic equations, and strict regex pipelines to quantify and guarantee reliability.

### Stochastic Reliability Equation

The overall probability of pipeline success $P(S)$ is modeled using a multiplicative decay equation across $n$ consecutive agent nodes, mitigated by our $k$-retry fallback mechanisms and heuristic routing:

$$ P(S) = \prod_{i=1}^{n} \left[ 1 - \left( \prod_{j=1}^{k_i} P(F_{ij}) \right) \right] $$

Where $P(F_{ij})$ represents the probability of failure for agent $i$ on retry $j$. Because our `SafeAgentWrapper` isolates failures, a single node's $P(F)$ does not catastrophically drop $P(S)$ to zero.

### Heuristic Decision Scoring

The `DynamicPlannerNode` doesn't just blindly follow LLM outputs. It uses a weighted heuristic function to validate state transitions before execution:

$$ H(node) = \alpha \cdot Confidence(LLM) + \beta \cdot Availability(API) - \gamma \cdot Penalty(RetryCount) $$

If $H(node) < \tau$ (where $\tau$ is our empirical threshold), the planner rejects the LLM's suggested route and deterministically falls back to the safest mathematical path, preventing infinite loops and unstable routing.

### Regex Sanitization Pipelines

LLM outputs are notoriously unpredictable. To ensure strict data integrity, all structural outputs pass through multiple regex-enforced sanitization pipelines before being committed to the PostgreSQL outbox:

- **JSON Payload Extraction:** `(?s)\{.*\}` heuristically isolates JSON from surrounding conversational hallucinations, ensuring clean parsing.
- **Strict Type Validation:** Advanced regex patterns pre-validate fields like emails (`^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$`) and UUIDs before passing them to the Pydantic parser, drastically reducing CPU cycles spent on failing serialization attempts.
- **Malicious Content Defense:** Regex pipelines actively scan for common injection patterns in user inputs and web-scraped data to maintain a clean system boundary.

---

## Graceful Degradation Hierarchy

The platform implements a multi-level graceful degradation strategy:

```mermaid
graph TB
    subgraph Level1["Level 1: Component Degradation"]
        L1A["LLM fails -> try next model in pool"]
        L1B["API provider fails -> skip source, continue polling others"]
        L1C["Scraping fails -> return empty result, let enricher compensate"]
    end

    subgraph Level2["Level 2: Agent Degradation"]
        L2A["Agent throws -> SafeAgentWrapper catches, records error"]
        L2B["Planner routes around failed agent"]
        L2C["Pipeline continues with partial data"]
    end

    subgraph Level3["Level 3: Workflow Degradation"]
        L3A["LLM routing fails -> deterministic fallback sequence"]
        L3B["Custom workflow fails -> fall back to linear execution"]
        L3C["All agents exhausted -> pipeline ends gracefully"]
    end

    subgraph Level4["Level 4: System Degradation"]
        L4A["Event processing crash -> outbox retry on next cycle"]
        L4B["DB connection lost -> NullPool prevents stale connections"]
        L4C["Process crash -> LangGraph checkpointer enables recovery"]
    end

    Level1 --> Level2
    Level2 --> Level3
    Level3 --> Level4
```

### Fallback Response Strategy

Every `generate_text()` call includes a hardcoded `fallback` parameter. If all LLM models are exhausted, the system returns a safe, parseable fallback rather than crashing:

```python
await self.llm_service.generate_text(
    prompt=prompt,
    fallback='{"next_node": "fallback", "reasoning": "fallback"}',  # Valid JSON
    require_json=True,
    strategy="fast"
)
```

---

## State Durability and Crash Recovery

### LangGraph Checkpointing

The entire workflow state is checkpointed to PostgreSQL via `AsyncPostgresSaver`:

```mermaid
graph LR
    LG["LangGraph Runtime"]
    CP["AsyncPostgresSaver"]
    PG["PostgreSQL"]

    LG -->|"After each step"| CP
    CP -->|"INSERT/UPDATE"| PG
    PG -->|"On recovery"| CP
    CP -->|"Restore state"| LG
```

If the process crashes mid-workflow, the state can be recovered from the last checkpoint, and the workflow can be resumed from where it left off.

### Intermediate State Persistence

Beyond checkpointing, the `WorkflowService` explicitly persists the current state to the `prospects` table after every agent execution:

```python
# After each on_chain_end event:
current_state = await self._app.aget_state(config)
async with async_session() as persist_session:
    ms = MemoryService(lambda s=persist_session: s)
    await ms.save_prospect_state(current_state.values)
```

This means the UI always reflects the latest state, even if the workflow is still running.

### Connection Pool Strategy

The database uses `NullPool` for the async engine, ensuring that every connection is created fresh and closed immediately:

```python
if not db_url.startswith("sqlite"):
    from sqlalchemy.pool import NullPool
    engine_kwargs["poolclass"] = NullPool
```

This prevents stale connections, connection leaks, and pool exhaustion in long-running processes -- a critical reliability measure for production deployments.

---

## Rate Limiting and Throttling

### Global LLM Rate Limiting

A global async lock enforces a minimum interval between LLM calls:

```mermaid
sequenceDiagram
    participant A as Agent A
    participant B as Agent B
    participant Lock as Global Lock
    participant Timer as Rate Timer

    A->>Lock: Acquire
    Lock-->>A: Granted
    A->>Timer: Check elapsed time
    Timer-->>A: 1.5s since last call
    A->>A: Sleep(1.0s) to reach 2.5s minimum
    A->>A: Call LLM
    A->>Lock: Release

    B->>Lock: Acquire
    Note over B,Lock: Blocked until A releases
    Lock-->>B: Granted
    B->>B: Call LLM immediately (2.5s elapsed)
    B->>Lock: Release
```

### Trigger Monitor Throttling

The trigger monitor implements two levels of throttling:

| Throttle | Duration | Purpose |
|:---|:---:|:---|
| Per-source interval | Configurable (default 3600s) | Respects configured polling frequency |
| Inter-provider sleep | 0.5s | Prevents burst rate limits across API providers |
| Inter-submission sleep | 15s | Protects free-tier LLM rate limits from pipeline floods |

---

## Observability and Monitoring

### Structured Logging

All logging uses `structlog` for machine-parseable structured output:

```python
logger.info("DynamicPlanner: LLM selected next node",
    prospect_id=prospect_id,
    next_node=next_node,
    reasoning=parsed.get("reasoning"))
```

### Execution Trace

The `execution_trace` in `GraphState` provides a complete audit trail:

```python
execution_trace: Annotated[list[dict], add_list]
```

Each trace record includes the agent name, timestamp, duration, thoughts, and state updates.

### PubSub Event Broadcasting

Real-time events are broadcast to connected SSE clients:

| Event Type | Content |
|:---|:---|
| `thought` | Agent reasoning and decisions |
| `action` | Agent completion notifications |
| `state_update` | Full state snapshot after each agent |

---

## Failure Scenario Analysis

| Scenario | Impact | Recovery Mechanism |
|:---|:---|:---|
| Single LLM model rate limited | None visible | Automatic rotation to next model in pool |
| All Groq models exhausted | Increased latency | Cascade to Gemini pool |
| All LLM models exhausted | Agent uses fallback response | Hardcoded fallback string |
| Agent throws unhandled exception | Agent skipped, error recorded | SafeAgentWrapper catches, planner routes around |
| LLM routing fails | Slightly suboptimal order | Deterministic fallback sequence |
| Database connection lost | Request fails | NullPool creates fresh connection on retry |
| Process crash during event processing | Event appears lost | Outbox cleanup retries on next poll cycle |
| Process crash during workflow | Workflow paused | LangGraph checkpointer enables resume |
| External API returns 429 | Call blocked temporarily | Circuit breaker trips, auto-recovers after timeout |
| External API goes down permanently | Service degraded | Circuit breaker stays OPEN, system works without that data |

---

<p align="center">
  <a href="README.md">Backend README</a> &#8226;
  <a href="CLASS_DIAGRAM.md">Class Diagrams</a> &#8226;
  <a href="SEQUENCE_FLOW.md">Sequence Flows</a> &#8226;
  <a href="SOLID_PRINCIPLES.md">SOLID</a> &#8226;
  <a href="AGENTIC_FLOW.md">Agentic Flow</a> &#8226;
  <a href="LLD_ARCHITECTURE.md">LLD</a> &#8226;
  <a href="APPLICATION_FLOW.md">App Flow</a>
</p>