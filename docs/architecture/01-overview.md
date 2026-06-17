# 01 -- System Architecture Overview

> **Updated**: 2026-06-17 | **Project**: SnapTrip E-Commerce Marketplace
>
> SnapTrip is a full-stack e-commerce marketplace platform with AI-powered features including
> semantic product search, personalized recommendations, and an LLM agent assistant.

## System Overview

SnapTrip is a complete online shopping platform consisting of:

- **Customer Mall (C-end)**: Product browsing, search, cart, checkout, member center
- **Admin Panel (B-end)**: Product management, order management, member management, promotions, CMS, RBAC
- **AI Agent System**: Multi-agent LangGraph architecture for product discovery, order assistance, recommendations, marketing, and admin analytics
- **Recommendation Engine**: Vector-embedding semantic search, collaborative filtering, hybrid search, trending detection, AB testing

The system is built as a monorepo (uv workspace) with Docker Compose orchestration.

---

## Architecture Layers

```
+---------------------------------------------------------------------------+
|                        PRESENTATION LAYER                                  |
|                                                                           |
|  +---------------------------+  +---------------------------------------+  |
|  | Admin Frontend (Vue 3)    |  | Customer Mall (Vue 3)                 |  |
|  | - Product Management (PMS)|  | - Home Page / Search / Product Detail|  |
|  | - Order Management (OMS)  |  | - Shopping Cart / Checkout           |  |
|  | - Promotion (SMS)         |  | - Member Center (orders/favorites)   |  |
|  | - Content (CMS)           |  | - Coupons / Brands / Categories      |  |
|  | - User/RBAC (UMS)         |  | - AI Chat Assistant                  |  |
|  +---------------------------+  +---------------------------------------+  |
+----------------------------------+----------------------------------------+
                                   | REST / SSE
                                   v
+---------------------------------------------------------------------------+
|                         API GATEWAY LAYER                                  |
|                         FastAPI (port 8000)                                 |
|                                                                           |
|  +---------------------------+  +---------------------------------------+  |
|  | Admin API (/admin/*)      |  | Portal API (/portal/*)               |  |
|  | - Product CRUD            |  | - Home feed / Recommendations        |  |
|  | - Order management        |  | - Product browsing / search          |  |
|  | - Member management       |  | - Cart / Checkout / Orders           |  |
|  | - Brand / Category        |  | - Member profile / favorites         |  |
|  | - Coupon / Flash sale     |  | - Coupons / Brands / Categories      |  |
|  | - CMS content             |  | - Search suggestions / autocomplete  |  |
|  | - RBAC (roles/menus/res)  |  | - Behavior tracking                  |  |
|  +---------------------------+  +---------------------------------------+  |
|                                                                           |
|  Middleware: JWT Auth | Rate Limiter | Unified {code,msg,data} response   |
+----------------------------------+----------------------------------------+
                                   |
                                   v
+---------------------------------------------------------------------------+
|                          SERVICE LAYER                                     |
|                                                                           |
|  +---------------------+  +---------------------+  +--------------------+ |
|  | Commerce Services    |  | Search Services      |  | AI Services        | |
|  | - product_service    |  | - vector_search      |  | - llm_gateway      | |
|  | - order_service      |  | - hybrid_search      |  | - agent graph      | |
|  | - cart_service       |  | - autocomplete       |  |                    | |
|  | - member_service     |  | - suggestion         |  |                    | |
|  | - coupon_service     |  | - query_expansion    |  |                    | |
|  | - flash_service      |  | - trending           |  |                    | |
|  | - cms_service        |  | - personalization    |  |                    | |
|  | - category_service   |  | - collaborative_     |  |                    | |
|  | - brand_service      |  |   filtering          |  |                    | |
|  |                      |  | - feature_service    |  |                    | |
|  |                      |  | - ab_test            |  |                    | |
|  |                      |  | - metrics            |  |                    | |
|  +---------------------+  +---------------------+  +--------------------+ |
+----------------------------------+----------------------------------------+
                                   |
                                   v
+---------------------------------------------------------------------------+
|                          AI AGENT LAYER (LangGraph)                        |
|                                                                           |
|  Supervisor-Specialist Multi-Agent Architecture                           |
|                                                                           |
|  +----------+ +----------+ +----------+ +----------+ +----------+         |
|  | Product  | | Order    | | Marketing| | Knowledge| | Admin    |         |
|  | Discovery| | Assistant| | Engine   | | QA       | | Analyst  |         |
|  +----------+ +----------+ +----------+ +----------+ +----------+         |
|  |                            |                                           |
|  +----------+                 v                                           |
|  |Compliance|     Recommendation Subgraph                                 |
|  +----------+     +--------+ +--------+ +--------+ +--------+ +---------+ |
|                   |User    | |Search  | |Product | |Inventory| |Marketing| |
|                   |Profile | |Intent  | |Rec     | |Check    | |Copy     | |
|                   +--------+ +--------+ +--------+ +--------+ +---------+ |
|                                                                           |
|  Tool System: Registry | Saga Transactions | Audit Tracing               |
+---------------------------------------------------------------------------+
                                   |
                                   v
+---------------------------------------------------------------------------+
|                          DATA LAYER                                        |
|                                                                           |
|  +---------------------+  +---------------------+  +--------------------+ |
|  | PostgreSQL 16       |  | Redis 7             |  | Elasticsearch 8    | |
|  | + pgvector (384d)   |  | - Celery broker     |  | - Full-text search | |
|  |                     |  | - Session cache     |  | - Product index    | |
|  | Tables:             |  | - Rate limit       |  |                    | |
|  | - Member (member,   |  | - SSE Pub/Sub      |  |                    | |
|  |   behavior)         |  |                     |  |                    | |
|  | - Product (product, |  +---------------------+  +--------------------+ |
|  |   sku, brand, cat,  |                                                   |
|  |   attribute)        |  +--------------------+  +--------------------+ |
|  | - Order (order,     |  | Celery Workers     |  | LiteLLM Proxy      | |
|  |   cart, return)     |  | - CF computation   |  | - LLM API gateway  | |
|  | - Promotion (coupon,|  | - Search indexing  |  | - Multi-model      | |
|  |   flash)            |  | - Order processing |  |   routing          | |
|  | - CMS (content)     |  | - Agent tasks      |  +--------------------+ |
|  | - RBAC (menu, role, |  +--------------------+                          |
|  |   resource, admin)  |                                                   |
|  | - Product Embedding |                                                   |
|  | - CF Vector         |                                                   |
|  +---------------------+                                                   |
+---------------------------------------------------------------------------+
```

---

## Deployment Architecture (Docker Compose)

```
                          docker compose up

+-------------------+  +-------------------+  +-------------------+
| marketplace :8000 |  | agent-worker      |  | agent-beat        |
|                   |  | (Celery Worker)   |  | (Celery Beat)     |
| FastAPI gateway   |  | LangGraph async   |  | Scheduled tasks   |
| + Celery Beat     |  | agent execution   |  | CF compute,       |
| Alembic migrations|  |                   |  | search indexing   |
+--------+----------+  +--------+----------+  +-------------------+
         |                      |
         v                      v
+--------+----------+  +--------+----------+  +-------------------+
| PostgreSQL 16     |  | Redis 7           |  | Elasticsearch 8   |
| pgvector          |  | broker/cache/     |  | product search    |
| :5432             |  | pubsub :6379      |  | :9200             |
+-------------------+  +-------------------+  +-------------------+
         |
         v
+--------+----------+  +-------------------+
| LiteLLM Proxy     |  | mall-web :5175    |
| LLM API gateway   |  | Customer SPA      |
| :4000             |  | (profile: full)   |
+-------------------+  +-------------------+
```

**Service Descriptions**:

| Service | Image | Port | Role |
|---------|-------|------|------|
| `postgres` | `pgvector/pgvector:pg16` | 5432 | Primary database with vector search extension |
| `redis` | `redis:7-alpine` | 6379 | Cache, Celery broker, SSE pub/sub |
| `elasticsearch` | `elasticsearch:8.15.3` | 9200 | Full-text product search engine |
| `litellm-proxy` | `ghcr.io/berriai/litellm` | 4000 | LLM API gateway (DeepSeek, Kimi routing) |
| `marketplace` | Backend Dockerfile.gateway | 8000 | FastAPI app + Celery Beat (auto-migrate on startup) |
| `agent-worker` | Backend Dockerfile.worker | -- | Celery worker for LangGraph agent execution |
| `agent-beat` | Backend Dockerfile.worker | -- | Celery Beat for scheduled tasks |
| `mall-web` | mall-web/Dockerfile | 80/5175 | Customer-facing Vue 3 SPA (profile: full) |

---

## Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Backend Framework** | Python 3.13 + FastAPI | REST API gateway for admin and portal |
| **Async Tasks** | Celery + Redis | Background jobs (CF, indexing, agents) |
| **Database** | PostgreSQL 16 + pgvector | Relational data + vector embeddings (384d) |
| **Search** | Elasticsearch 8 | Full-text product search |
| **Cache / PubSub** | Redis 7 | Session cache, rate limiting, SSE events |
| **AI Agent** | LangGraph | Multi-agent orchestration with supervisor routing |
| **LLM Gateway** | LiteLLM Proxy | Unified LLM API with model routing |
| **Embedding** | HuggingFace (384d) | Product semantic embeddings via local model |
| **Admin Frontend** | Vue 3 + Vite + TypeScript + Element Plus | Admin dashboard SPA |
| **Customer Mall** | Vue 3 + Vite + TypeScript + Tailwind CSS | Customer shopping SPA |
| **Monorepo** | uv workspace | Python package management |
| **Migrations** | Alembic | Database schema versioning |
| **CI/CD** | GitHub Actions | Lint, test, Docker build |
| **Containerization** | Docker Compose | Multi-service deployment |

---

## Key Data Flows

### 1. Product Search Flow

```
User types query --> mall-web SearchView
  --> GET /portal/product?keyword=...&page=1&sort=...
  --> HybridSearchService
    --> Elasticsearch full-text query (product name, description, brand)
    --> pgvector semantic search (cosine similarity on product_embedding)
    --> Merge & rerank results
    --> Return paginated product list
  <-- Frontend renders product cards
```

### 2. Order Placement Flow

```
User adds items --> Cart (Redis / PostgreSQL)
  --> CartView --> OrderConfirmView
  --> POST /portal/order/generateConfirmOrder
    --> Validate stock (SKU inventory)
    --> Apply coupons (if any)
    --> Calculate total (product price - discount + shipping)
  --> POST /portal/order/generateOrder
    --> Deduct inventory (atomic)
    --> Create order record
    --> Create order items
    --> Clear cart items
  --> PayView
    --> POST /portal/order/paySuccess
    --> Order status: unpaid --> paid
```

### 3. AI Recommendation Flow

```
User on ProductDetailView / HomeView
  --> POST /portal/recommendation/*
  --> Agent Worker (Celery)
    --> Recommendation Subgraph (LangGraph)
      1. UserProfile node: Load member behavior history, preferences
      2. SearchIntent node: Parse user context into structured intent
      3. ProductRec node: Query collaborative filtering vectors + embeddings
      4. Inventory node: Filter by stock availability
      5. MarketingCopy node: Generate personalized product descriptions (LLM)
    --> Return ranked product list with AI-generated copy
  <-- Frontend renders AI recommendation section
```

### 4. Admin Product Management Flow

```
Admin logs in --> JWT auth
  --> Admin Dashboard
  --> PMS (Product Management System)
    --> CRUD operations on products, SKUs, brands, categories, attributes
    --> Product creation triggers:
      - Embedding generation (Celery task)
      - Elasticsearch indexing (Celery task)
      - CF vector update
```

### 5. AI Customer Service Flow

```
User initiates CS chat
  --> POST /portal/cs/chat { message, session_id }
  --> Agent Worker (Celery)
    --> LangGraph Main Graph
      1. Supervisor: Classify intent (cs_after_sales/complaint/inquiry)
      2. CustomerService node:
         - Emotion detection (angry/frustrated/anxious/satisfied/neutral)
         - Emotion trajectory analysis (multi-turn)
         - Inject tone hints into system prompt
         - LLM reasoning + tool selection (14 tools available)
      3. Tool execution via ToolHarness (auth → rate limit → trace → audit)
      4. Tool results back to CustomerService for next reasoning step
      5. Loop until LLM produces final answer
      6. Synthesize → Compliance check → Response
    --> SSE stream: node_started → tool_called → tool_finished → message
  <-- Frontend renders AI response + action cards
```

### 6. Search Discovery (Home Feed) Flow

```
User opens homepage
  --> GET /portal/home/feed
  --> 5 data sources concurrent fetch:
      1. AI Recommendations (LangGraph 4-Agent pipeline)
      2. Trending Products (Redis time-bucket ZSET, Reddit Hot algorithm)
      3. New Products (DB query, published in last 7 days)
      4. Viewed History (Redis sliding window, last 50 products)
      5. Search Discovery (AI-generated suggestions + popular queries)
  --> Merge & deduplicate across sources
  <-- Frontend renders personalized home feed sections
```

---

## Monorepo Package Structure

```
snaptrip/
├── pyproject.toml              # uv workspace root
├── docker-compose.yml           # 8-service orchestration
├── Makefile / Taskfile.yml      # Build & run commands
│
├── backend/                     # Python backend monolith
│   ├── marketplace/app/
│   │   ├── api/admin/          # Admin panel routes (18 files)
│   │   ├── api/portal/         # Customer portal routes (15 files)
│   │   ├── models/             # ORM models (member, product, order, promotion, cms, rbac)
│   │   ├── schemas/            # Pydantic request/response schemas
│   │   ├── services/           # Business logic (25+ services)
│   │   ├── search/             # Elasticsearch client
│   │   ├── tasks/              # Celery task definitions
│   │   └── core/               # Config, security, exceptions
│   ├── alembic/                # Database migrations
│   └── tests/                  # Unit + integration tests
│
├── agent/                       # AI Agent system
│   └── src/agent/
│       ├── graph.py            # LangGraph main graph definition
│       ├── nodes/              # Supervisor + specialist nodes
│       │   └── recommendation/ # Recommendation subgraph
│       ├── schemas/            # Agent state/event schemas
│       ├── tools/              # Tool registry + implementations
│       ├── ports/              # Abstract interfaces (LLM, tools, events)
│       ├── adapters/           # Adapter implementations
│       └── services/           # Agent services + LLM gateway
│
├── frontend/                    # Admin panel (Vue 3 + Element Plus)
│   └── src/
│       ├── views/              # PMS, OMS, SMS, CMS, UMS, settings
│       ├── apis/               # API client modules
│       └── stores/             # Pinia state management
│
├── mall-web/                    # Customer mall (Vue 3 + Tailwind)
│   └── src/
│       ├── views/              # Home, Search, Product, Cart, Member
│       ├── apis/               # API client modules
│       └── stores/             # Pinia state management
│
├── shared/                      # Cross-package shared library
│   └── snaptrip_shared/
│       ├── core/               # Config, logging, exceptions, security
│       ├── db/                  # Session, Redis
│       └── schemas/            # Shared Pydantic models
│
├── litellm/                     # LiteLLM proxy config
│   └── config.yaml
│
└── docs/                        # Project documentation
```

---

## Key Architecture Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Backend pattern | Modular monolith (marketplace app) | Avoids distributed complexity; clear directory separation supports future microservice extraction |
| Agent framework | LangGraph StateGraph | Native state persistence, interrupt/resume for human-in-loop, conditional routing |
| Agent architecture | Supervisor-Specialist | Single supervisor routes to domain specialists; each specialist is independently testable |
| LLM gateway | LiteLLM Proxy | Unified API for multiple providers (DeepSeek, Kimi); cost tracking; model fallback |
| Product search | Elasticsearch + pgvector Hybrid | ES for keyword/text matching, pgvector for semantic similarity; hybrid ranking |
| Product embedding | HuggingFace local model (384d) | Offline inference, no API cost, consistent dimensions |
| Vector dimension | 384 (not 1536) | Migrated from OpenAI text-embedding-3-small (1536d) to local HuggingFace model (384d) |
| Collaborative filtering | Custom CF vectors + pgvector | User-item interaction matrix stored as vectors for similarity-based recommendation |
| Frontend framework | Vue 3 + Vite + TypeScript | Two separate SPAs: admin (Element Plus) and mall (Tailwind CSS) |
| Monorepo tool | uv workspace | Fast dependency resolution, unified lock file, shared library |
| Deployment | Docker Compose (8 services) | Single-machine production; scales horizontally by adding worker replicas |
| Auth | JWT with refresh token rotation | Stateless access tokens (15min) + SHA256-hashed refresh tokens (7d) with rotation |
| Agent specialist design | Single-inheritance BaseSpecialist | Template method pattern eliminates ~45 lines of boilerplate per specialist; each independently testable |
| Agent tool system | ToolHarness singleton + Hook chain | Single entry point for all tool calls; Auth/RateLimit/Trace/Audit/Alert as composable hooks |
| Transaction safety | Saga (Reserve→Confirm→Rollback) + Compensation LIFO | Multi-tool operations maintain consistency; compensation registry enables partial failure recovery |
| Audit integrity | SHA-256 hash chain (AuditStore) | Each entry links to previous via cryptographic hash; verify_chain() detects tampering |
| Content safety | Regex compliance check (non-blocking) | PII + advertising law keyword scanning <2ms; violations logged but response not blocked |
| Emotion awareness | Keyword-based emotion detection | 5-class detection + multi-turn trajectory, injected into CustomerService system prompt for tone adjustment |
| Model resilience | 4-level fallback chain + tenacity retry | DeepSeek V4 Pro → Flash → Kimi K2.6 → K2.5; 3 retries per level with exponential backoff |
| Customer service | AI-first with human escalation path | AI handles common issues via 14 tools; SLA breach triggers agent notification; ticket-based handoff |
| Search discovery | 5-source concurrent homefeed aggregation | AI recs + trending + new + history + discovery merged at API layer; graceful degradation per source |
