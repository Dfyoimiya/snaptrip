# CLAUDE.md — SnapTrip Developer Guide

## Project Overview

SnapTrip is a full-stack e-commerce marketplace platform built as a Python monorepo. It comprises a FastAPI backend, an AI agent system (LangGraph), an admin dashboard (Vue 3 + Element Plus), and a customer-facing shopping website (Vue 3 + Tailwind). The codebase evolved from an earlier travel-planning agent system and now serves as a general-purpose commerce platform with AI-powered search, recommendations, and assistant features.

## Monorepo Structure

```
snaptrip/
├── backend/          # Python FastAPI backend (marketplace API + Celery worker)
│   ├── app/          # Application layer: api/, models/, schemas/, services/, search/, tasks/
│   ├── marketplace/  # Package entry point: main.py, celery_app.py
│   ├── alembic/      # Database migrations (async mode)
│   └── tests/        # unit/ and integration/ test suites
├── agent/            # AI agent system (LangGraph StateGraph)
│   └── src/agent/    # graph, nodes, tools, runtime, adapters, events, services, schemas
├── shared/           # Shared Python library (snaptrip_shared)
│   └── snaptrip_shared/  # core/, db/ — used by backend and agent
├── contracts/        # Interface contracts: ports/ (abstract interfaces), schemas/ (shared Pydantic)
├── frontend/         # B-end admin dashboard (Vue 3 + Element Plus + TypeScript)
├── mall-web/         # C-end customer shopping website (Vue 3 + Vite + TypeScript + Tailwind)
├── litellm/          # LiteLLM proxy config (LLM API gateway)
├── nginx/            # Nginx reverse proxy configuration
└── docs/             # Project documentation
```

The **uv workspace** includes `backend/`, `shared/`, `agent/`, and `contracts/`. Frontend projects (`frontend/`, `mall-web/`) are **not** part of the uv workspace.

## Quick Start

```bash
# 1. Install dependencies
make init              # uv sync + npm install (both frontends)

# 2. Start full development stack (postgres, redis, es, litellm, marketplace, agent-worker, mall-web)
make dev               # Docker Compose with hot-reload (development target)

# 3. Or start services individually
make backend-dev       # FastAPI with uvicorn --reload on :8000
make frontend-dev      # Admin dashboard Vite HMR
make mall-web-dev      # Customer mall Vite HMR
```

**Prerequisites:** Docker, uv, Python 3.13+, Node.js 20+.

**Environment:** Copy `.env.example` to `.env` (done automatically by `make init`). All secrets are managed via environment variables, never committed.

## Key Commands

### Development

| Command | Description |
|---|---|
| `make dev` | Full stack via Docker Compose (development target, hot-reload) |
| `make build` | Build all Docker images |
| `make up` | Production mode stack |
| `make down` | Stop all services |
| `make logs` | Tail Docker Compose logs |
| `make backend-dev` | Backend only — `uv run uvicorn marketplace.app.main:app --reload` |
| `make frontend-dev` | Admin frontend only — `npm run dev` |
| `make mall-web-dev` | Customer mall only — `npm run dev` |

### Database

| Command | Description |
|---|---|
| `make migrate` | Generate alembic migration (autogenerate) |
| `make migrate-up` | Apply all pending migrations |
| `make migrate-down` | Rollback last migration |
| `make seed` | Seed development data (users, menus, products) |
| `make dev-init` | Run migrations + seed in one step |

### Testing

| Command | Description |
|---|---|
| `make test` | Run all backend tests (unit + integration) |
| `make test-unit` | Unit tests with coverage |
| `make test-integration` | Integration tests (requires test DB) |
| `make test-up` | Start test database (pgvector:5433, redis:6380) |
| `make test-down` | Stop test database |

### Code Quality

| Command | Description |
|---|---|
| `make lint` | Ruff check + mypy across backend, agent, shared |
| `make format` | Ruff format across backend, agent, shared |
| `make lint-frontend` | TypeScript type-check (admin frontend) |

### Other

| Command | Description |
|---|---|
| `make backend-shell` | Bash into marketplace container |
| `make clean` | Remove containers, volumes, __pycache__, node_modules |

## Architecture

### Backend (`backend/`)

- **Entry point:** `marketplace/app/main.py` — FastAPI app with lifespan-managed services
- **API routes** organized into two domains:
  - `app/api/admin/` — 18 route files for admin dashboard (product, order, member, brand, category, coupon, flash, CMS, dashboard, menu, resource, role, admin user, attribute, return_apply, return_reason, order_setting)
  - `app/api/portal/` — 15 route files for customer portal (product, cart, order, coupon, home, homefeed, brand, category, member, notice, recommendation, search_suggest, behavior)
- **Models:** SQLAlchemy 2.0 async models across domains: member, product, order, promotion, cms, rbac
- **Services:** 25+ service files covering product, order, member, cart, coupon, search (vector/hybrid), collaborative filtering, autocomplete, trending, A/B testing, metrics, and more
- **Search:** Elasticsearch for full-text search (`app/search/client.py`), pgvector for semantic/vector search
- **Async tasks:** Celery workers handle CF computation, search indexing, order processing (`app/tasks/`)
- **Config:** Pydantic Settings — `Settings` (general) + `CommerceSettings` (env_prefix `COMMERCE_`)
- **Auth:** JWT with refresh token rotation, RBAC for admin permissions

### Agent (`agent/`)

- **Orchestration:** LangGraph `StateGraph` with supervisor-specialist pattern
- **Flow:** `supervisor` -> `route_by_intent` -> specialist (product_discovery, order_assistant, marketing_engine, knowledge_qa, admin_analyst) <-> `tool_node` -> `synthesize` -> `compliance_check` -> END
- **Specialists** are LangChain-based nodes that handle conversational intents and call tools
- **Tools** are registered via `ToolRegistry` with a `ToolHarness` for context and hooks
- **Recommendation subgraph** in `nodes/recommendation/` for personalized product recommendations
- **Events:** Redis PubSub event bus for async communication
- **Runtime:** `AgentRuntime` is the DI container holding the LLM adapter, tool harness, and session context

### Frontends

- **`frontend/`** — Admin dashboard (Vue 3 + Element Plus + Pinia + Vue Router)
  - Modules: PMS (product), OMS (order), SMS (promotion), CMS (content), UMS (user), AI Assistant
  - API layer: 25+ API modules in `src/api/`
- **`mall-web/`** — Customer shopping website (Vue 3 + Vite + TypeScript + Tailwind CSS)
  - Views: Home, Search, ProductDetail, Cart, Checkout, Brand, Category, Coupons, Member Center
  - JWT auth with auto-refresh token rotation
  - Router with navigation guards

### Infrastructure

- **PostgreSQL 16** with pgvector extension (vector embeddings)
- **Redis 7** — Celery broker, SSE PubSub, caching
- **Elasticsearch 8** — full-text product search
- **LiteLLM** — LLM API proxy (gateway for DeepSeek, Kimi models)
- **Nginx** — reverse proxy
- **CI:** GitHub Actions — lint (ruff + mypy), frontend type-check, unit + integration tests with coverage

### Docker Services (`docker-compose.yml`)

| Service | Port | Description |
|---|---|---|
| postgres | 5432 | PostgreSQL 16 + pgvector |
| redis | 6379 | Redis 7 (cache, broker, pubsub) |
| elasticsearch | 9200 | Elasticsearch 8 (full-text search) |
| litellm-proxy | 4000 | LiteLLM API gateway |
| marketplace | 8080 | FastAPI + Celery Beat |
| agent-worker | — | Celery worker (LangGraph async execution) |
| agent-beat | — | Celery Beat scheduler |
| mall-web | 5175 | Customer-facing Vue app |

## Conventions

### Code Style

- **Line length:** 120 characters (ruff config)
- **Python target:** 3.11+
- **Ruff rules:** E, F, I, N, UP, B, SIM (with B008 ignored)
- **Mypy:** strict-ish — `warn_return_any`, `warn_unused_configs`, `check_untyped_defs`, Pydantic plugin
- **Formatting** is handled by `ruff format` (pre-commit hook enforces it)
- **Imports:** Use `from __future__ import annotations` for all new Python files
- **Type annotations:** Use `| None` syntax (not `Optional[]`), `list[dict]` (not `List[Dict]`)

### API Patterns

- All API routes use Pydantic schemas for request/response models (located in `app/schemas/`)
- Service layer handles business logic; route handlers are thin
- Database sessions are managed via `snaptrip_shared.db.session`
- Async throughout — all DB operations use SQLAlchemy 2.0 async style
- Portal routes are under `/api/v1/portal/`, admin routes under `/api/v1/admin/`

### Git

- **Branch:** `dev` (active), `main` (production)
- **Commit style:** Conventional commits preferred — `feat:`, `fix:`, `refactor:`, `chore:`
- **Pre-commit hooks:** Ruff format + lint (backend files only), trailing whitespace, end-of-file fixer, YAML/TOML validation, merge conflict detection, private key detection
- Never commit `.env` files or secrets

### Testing

- **Unit tests:** `backend/tests/unit/` — no external dependencies
- **Integration tests:** `backend/tests/integration/` — requires test DB/Redis
- **Pytest markers:** `unit`, `integration`, `amap` (skip in CI with `-m "not amap"`), `ci`, `slow`
- **Coverage:** cov on marketplace, agent, and snaptrip_shared packages
- Test DB runs on postgres:5433 and redis:6380 (separate from dev)

### Package Management

- Always use **uv** — `uv run` for Python commands, `uv sync` for dependencies
- Never use pip directly within the monorepo
- Workspace dependencies declared in root `pyproject.toml`, per-package deps in each subdirectory's `pyproject.toml`
- Frontend dependencies managed by npm (package-lock.json committed)
