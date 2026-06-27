# Phase 1 Verification Guide

This document describes how to verify that the Phase 1 infrastructure migration (SQLite → PostgreSQL) is working correctly.

---

## Prerequisites

- Docker and Docker Compose installed
- A valid LLM API key (OpenAI, Gemini, or Groq)

---

## 1. Start Local PostgreSQL

```bash
# Start only the PostgreSQL service
docker compose up postgres -d

# Verify it's healthy
docker compose ps
# Should show "healthy" status for icp-postgres
```

---

## 2. Set Environment Variables

Copy the example environment file and fill in your values:

```bash
cp .env.example .env
# Edit .env with your LLM_API_KEY
```

Key variables:
| Variable | Required | Example |
|---|---|---|
| `DATABASE_URL` | ✅ | `postgresql://agent:agent@localhost:5432/agentic` |
| `LLM_API_KEY` | ✅ | `sk-...` or Gemini/Groq key |
| `LLM_PROVIDER` | No (default: `openai`) | `openai`, `gemini`, `groq` |
| `LLM_MODEL` | No (default: `gpt-4o`) | `gpt-4o`, `gemini-2.0-flash`, `llama-3.3-70b-versatile` |

---

## 3. Run Migrations & Start the App

### Option A: Via Docker Compose (recommended)

```bash
# Build and start everything
docker compose up --build

# Expected output:
# icp-agent-api  | Running database migrations...
# icp-agent-api  | INFO  [alembic.runtime.migration] Running upgrade  -> <revision>, Initial schema
# icp-agent-api  | Starting Uvicorn...
# icp-agent-api  | INFO:     Application startup complete.
```

### Option B: Local development (without Docker for the app)

```bash
# Ensure PostgreSQL is running (via Docker or native install)
# Activate your virtualenv
pip install -r requirements.txt

# Run migrations
alembic upgrade head

# Start the app
python app.py
```

---

## 4. Verify Database Tables

Connect to PostgreSQL and check that tables were created:

```bash
docker compose exec postgres psql -U agent -d agentic -c "\dt"
```

Expected tables:
- `prospects`
- `hitl_requests`
- `config`
- `trigger_sources`
- `processed_events`
- `checkpoint_blobs` (LangGraph)
- `checkpoint_writes` (LangGraph)
- `checkpoints` (LangGraph)

---

## 5. HITL Container Restart Test

This is the critical test — proving that workflow state survives container restarts.

### Step 1: Submit a prospect

```bash
curl -X POST http://localhost:8000/api/prospects \
  -H "Content-Type: application/json" \
  -d '{"company_name": "Acme Corp", "website": "https://acme.com", "trigger_event": "manual_test"}'
```

Note the returned `prospect_id`.

### Step 2: Wait for HITL pause

```bash
# Check for pending HITL requests
curl http://localhost:8000/api/hitl/pending
```

When the workflow reaches the HITL gateway, you should see a pending request.

### Step 3: Restart the container

```bash
# Stop the app container (PostgreSQL keeps running)
docker compose stop icp-agent-api

# Restart it
docker compose start icp-agent-api
```

### Step 4: Verify state persistence

```bash
# The same HITL request should still be pending
curl http://localhost:8000/api/hitl/pending

# The prospect should still have its state
curl http://localhost:8000/api/prospects/<prospect_id>
```

### Step 5: Resume the workflow

```bash
# Approve the HITL request
curl -X POST http://localhost:8000/api/hitl/<request_id>/approve \
  -H "Content-Type: application/json" \
  -d '{}'
```

The workflow should resume from where it paused — proving that the PostgreSQL checkpointer works correctly across restarts.

---

## 6. Expected Log Output

On a successful startup, you should see:

```
Running database migrations...
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
Starting Uvicorn...
INFO:     Started server process
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

---

## Troubleshooting

| Issue | Solution |
|---|---|
| `DATABASE_URL is required` | Set `DATABASE_URL` in `.env` or as an environment variable |
| `connection refused` to PostgreSQL | Ensure the postgres service is running and healthy |
| `psycopg` import error | Run `pip install psycopg[binary]` |
| `asyncpg` import error | Run `pip install asyncpg` |
| HITL state lost after restart | Verify `DATABASE_URL` points to PostgreSQL (not SQLite) |
