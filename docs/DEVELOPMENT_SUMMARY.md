# SnapTrip Development Summary

> **Version**: 1.0.0 | **Date**: 2026-06-17
>
> SnapTrip is a full-stack e-commerce marketplace platform with AI-powered search,
> recommendations, and an LLM agent assistant.

---

## Module Inventory

### Backend Models (`backend/app/models/`)

| Directory | Table/Model | Purpose |
|-----------|------------|---------|
| `member/` | `Member` | Customer accounts (email, password, nickname, avatar, phone, status) |
| `member/` | `MemberBehavior` | User behavior tracking (product views, searches, cart, purchases) |
| `product/` | `Product` | Product catalog (name, description, price, brand, category, pictures, stock) |
| `product/` | `Sku` | Product SKUs (specs, price, stock, picture) |
| `product/` | `Brand` | Brand management (name, logo, description, factory status) |
| `product/` | `Category` | Product category tree (parent_id, name, level, icon, nav_status) |
| `product/` | `ProductAttribute` | Product attributes (type, name, input_type, values) |
| `product/` | `ProductEmbedding` | Product semantic embeddings (vector(384) for pgvector) |
| `product/` | `ProductCFVector` | Collaborative filtering vectors |
| `order/` | `Order` | Orders (member, status, total, pay, delivery info) |
| `order/` | `OrderItem` | Line items within an order |
| `order/` | `CartItem` | Shopping cart items (member, product, sku, quantity) |
| `order/` | `ReturnApply` | Return/refund request |
| `order/` | `ReturnReason` | Return reason dictionary |
| `order/` | `OrderSetting` | Order config (auto-cancel, auto-confirm timers) |
| `promotion/` | `Coupon` | Coupon template (type, amount, threshold, count, dates) |
| `promotion/` | `FlashPromotion` | Flash sale sessions and product relations |
| `cms/` | `CmsContent` | CMS content (help articles, banners, notices) |
| -- | `Menu` | Admin sidebar menu tree |
| -- | `Role` | RBAC role definition |
| -- | `Resource` | RBAC resource (API permissions) |
| -- | `RoleResourceRelation` | Many-to-many role-resource mapping |
| -- | `UmsAdmin` | Admin user accounts |
| -- | `Checkpoint` | Agent plan checkpoint snapshots |
| -- | `LlmUsageLog` | LLM call cost tracking |
| -- | `TripHistory` | User trip view history |

### Backend API Routes

**Admin Panel** (`backend/app/api/admin/`) -- 19 route files:

| File | Domain | Key Endpoints |
|------|--------|--------------|
| `product.py` | PMS | CRUD products, SKUs, attributes |
| `order.py` | OMS | Order list, detail, delivery, close |
| `member.py` | UMS | Member list, detail, status management |
| `brand.py` | PMS | Brand CRUD |
| `category.py` | PMS | Category CRUD with tree |
| `attribute.py` | PMS | Product attribute CRUD |
| `coupon.py` | SMS | Coupon template CRUD |
| `flash.py` | SMS | Flash sale session and product management |
| `cms.py` | CMS | Content CRUD, statistics |
| `dashboard.py` | -- | Admin dashboard statistics |
| `menu.py` | RBAC | Sidebar menu management |
| `role.py` | RBAC | Role CRUD with resource assignment |
| `resource.py` | RBAC | Resource CRUD (categories + items) |
| `ums_admin.py` | UMS | Admin user account management |
| `order_setting.py` | OMS | Order timer configuration |
| `return_apply.py` | OMS | Return request processing |
| `return_reason.py` | OMS | Return reason dictionary |

**Customer Portal** (`backend/app/api/portal/`) -- 13 route files:

| File | Domain | Key Endpoints |
|------|--------|--------------|
| `product.py` | Products | Product list/detail, category products |
| `cart.py` | Cart | Add/update/delete/clear cart |
| `order.py` | Orders | Generate confirm order, place order, pay, list, detail |
| `member.py` | Member | Register, login, profile, favorites, address |
| `homefeed.py` | Feed | Home page feed with personalization |
| `recommendation.py` | AI Rec | Get personalized product recommendations |
| `search_suggest.py` | Search | Search suggestions, autocomplete, trending |
| `behavior.py` | Tracking | Submit user behavior events |
| `coupon.py` | Coupons | Available coupons, member coupons |
| `brand.py` | Brands | Brand list/detail |
| `category.py` | Categories | Product category tree |
| `notice.py` | Notices | Notice list/detail |
| `home.py` | Home | Home page banner/feed data |

### Backend Services (`backend/app/services/`)

| Service | Purpose |
|---------|---------|
| `product_service.py` | Product CRUD, SKU management, category tree building |
| `order_service.py` | Order creation, payment, status transitions, delivery |
| `cart_service.py` | Cart CRUD, merge, clear |
| `member_service.py` | Member registration, authentication, profile management |
| `coupon_service.py` | Coupon distribution, usage, expiry |
| `flash_service.py` | Flash sale scheduling and product relations |
| `cms_service.py` | CMS content CRUD |
| `category_service.py` | Category tree management |
| `brand_service.py` | Brand CRUD |
| `vector_search_service.py` | pgvector semantic product search |
| `hybrid_search_service.py` | Elasticsearch + pgvector hybrid search with reranking |
| `autocomplete_service.py` | Search autocomplete suggestions |
| `suggestion_service.py` | Related search suggestions |
| `query_expansion_service.py` | Query rewriting and expansion |
| `search_personalization_service.py` | Personalized search ranking |
| `trending_service.py` | Trending product detection |
| `collaborative_filtering_service.py` | User-based CF vector computation |
| `feature_service.py` | Feature engineering for search/recommendation |
| `ab_test.py` | AB testing framework |
| `metrics.py` | Business and model performance metrics |
| `memory_service.py` | Redis-backed session memory and cache management |

### Backend Tasks (`backend/app/tasks/`)

| Task | Purpose |
|------|---------|
| `cf_tasks.py` | Collaborative filtering vector computation (scheduled) |
| `index_tasks.py` | Elasticsearch product indexing (scheduled) |
| `order_tasks.py` | Order auto-cancel, auto-confirm (scheduled) |

### Backend Search (`backend/app/search/`)

| File | Purpose |
|------|---------|
| `client.py` | Elasticsearch client initialization and connection management |

### AI Agent System (`agent/src/agent/`)

**Graph & Runtime**:

| File | Purpose |
|------|---------|
| `graph.py` | Main LangGraph StateGraph definition with supervisor routing |
| `runtime.py` | AgentRuntime DI container, service injection |
| `tool_node.py` | LangGraph tool node for tool execution |
| `utils.py` | Agent utility functions |

**Agent Nodes** (`agent/src/agent/nodes/`):

| Node | Domain | Purpose |
|------|--------|---------|
| `supervisor.py` | Orchestration | Routes user requests to appropriate specialist |
| `product_discovery.py` | Product | Product search and discovery specialist |
| `order_assistant.py` | Orders | Order status, tracking, issue resolution specialist |
| `marketing_engine.py` | Marketing | Campaign, coupon, promotion specialist |
| `knowledge_qa.py` | Knowledge | FAQ and product knowledge specialist |
| `admin_analyst.py` | Admin | Data analysis and reporting specialist |
| `compliance.py` | Safety | Content moderation and compliance specialist |
| `synthesize.py` | Output | Synthesize multi-specialist outputs |
| `trace.py` | Observability | Execution tracing |
| `base.py` | Base | Base specialist class with shared logic |

**Recommendation Subgraph** (`agent/src/agent/nodes/recommendation/`):

| Node | Purpose |
|------|---------|
| `graph.py` | Subgraph definition for recommendation pipeline |
| `supervisor.py` | Subgraph supervisor routing |
| `user_profile.py` | User profiling from behavior history |
| `search_intent.py` | Search intent parsing from user context |
| `product_rec.py` | Product recommendation using CF + embeddings |
| `inventory.py` | Inventory/stock availability checking |
| `marketing_copy.py` | AI-generated marketing copy for products |
| `base.py` | Base node class for recommendation nodes |

**Tool System** (`agent/src/agent/tools/`):

| Directory/File | Purpose |
|----------------|---------|
| `registry/registry.py` | Tool registration and discovery |
| `registry/schema.py` | Tool schema definitions |
| `implementations/search_products.py` | Product search tool |
| `implementations/get_product_detail.py` | Product detail tool |
| `implementations/query_order.py` | Order query tool |
| `implementations/cancel_order.py` | Order cancellation tool |
| `implementations/get_coupons.py` | Coupon listing tool |
| `implementations/search_knowledge.py` | Knowledge base search tool |
| `implementations/base.py` | Base tool class |
| `harness/` | Tool execution harness |
| `tracing/` | Tool call audit tracing |
| `transaction/` | Saga transaction coordinator |
| `bootstrap.py` | Tool system initialization |
| `auth.py` | Tool auth/delegation |

**Ports & Adapters** (`agent/src/agent/ports/`, `agent/src/agent/adapters/`):

| File | Purpose |
|------|---------|
| `ports/llm.py` | LLM port protocol |
| `ports/tools.py` | Tool gateway port protocol |
| `ports/events.py` | Event sink port protocol |
| `ports/repositories.py` | Repository port protocols |
| `adapters/langchain_adapter.py` | LangChain/LiteLLM adapter |
| `adapters/persistence/plan_run.py` | Plan run persistence adapter |
| `adapters/persistence/runtime_event.py` | Runtime event persistence adapter |

**Schemas** (`agent/src/agent/schemas/`):

| File | Purpose |
|------|---------|
| `state.py` | Agent runtime state schema |
| `events.py` | Runtime event schema |
| `llm.py` | LLM interaction schemas |
| `recommendation.py` | Recommendation pipeline schemas |

---

## Frontend Inventory

### Admin Panel (`frontend/src/`)

**Views** (10 modules):

| Module | Directory | Pages |
|--------|-----------|-------|
| PMS | `views/pms/` | Product list, product detail/edit, product category, product attributes |
| OMS | `views/oms/` | Order list, order detail, return management |
| SMS | `views/sms/` | Coupon management, flash sale management |
| CMS | `views/cms/` | Content list/edit, banners, statistics |
| UMS | `views/ums/` | Admin user management, member management |
| RBAC | `views/layout/`, `views/normal/` | Roles, menus, resources |
| Dashboard | `views/home/` | Admin dashboard |
| Settings | `views/setting/` | System settings |
| Login | `views/login/` | Admin login |
| AI | `views/ai/` | AI assistant chat panel |

**API Modules** (27 files): Full API client for all admin endpoints.

### Customer Mall (`mall-web/src/`)

**Views** (21 pages):

| View | Purpose |
|------|---------|
| `HomeView.vue` | Home page with banners, categories, recommendations |
| `SearchView.vue` | Product search with filters and autocomplete |
| `ProductDetailView.vue` | Product detail with specs, SKUs, reviews |
| `CartView.vue` | Shopping cart management |
| `OrderConfirmView.vue` | Checkout / order confirmation |
| `OrderDetailView.vue` | Order detail and tracking |
| `PayView.vue` | Payment page |
| `PaySuccessView.vue` | Payment success confirmation |
| `LoginView.vue` / `RegisterView.vue` | Authentication |
| `BrandView.vue` / `BrandDetailView.vue` | Brand browsing |
| `CategoryView.vue` | Category-based product browsing |
| `CouponCenterView.vue` | Available coupons |
| `HotProductView.vue` / `NewProductView.vue` | Curated product lists |
| `NoticeListView.vue` / `NoticeDetailView.vue` | Site notices |
| `HelpView.vue` | Help center |
| `AboutView.vue` | About page |
| `NotFoundView.vue` | 404 page |
| `member/` | Member center (orders, favorites, addresses, history) |

---

## Database Table Inventory

### Member Domain

| Table | Description |
|-------|------------|
| `member` | Customer accounts with profile fields |
| `member_behaviors` | User behavior event log |

### Product Domain

| Table | Description |
|-------|------------|
| `product` | Product catalog master table |
| `sku` | Product SKUs with specs and pricing |
| `brand` | Brand dictionary |
| `category` | Product category tree |
| `product_attribute` | Attribute definitions |
| `product_attribute_value` | Attribute values per product |
| `product_embeddings` | Semantic embeddings (vector(384)) |
| `product_cf_vectors` | Collaborative filtering vectors |

### Order Domain

| Table | Description |
|-------|------------|
| `order` | Orders with status lifecycle |
| `order_item` | Line items per order |
| `cart_item` | Shopping cart items |
| `return_apply` | Return/refund requests |
| `return_reason` | Return reason dictionary |
| `order_setting` | Order automation config |

### Promotion Domain

| Table | Description |
|-------|------------|
| `coupon` | Coupon template definitions |
| `coupon_history` | Coupon assignment and usage records |
| `flash_promotion` | Flash sale session definitions |
| `flash_promotion_product_relation` | Products in flash sales |

### CMS Domain

| Table | Description |
|-------|------------|
| `cms_content` | Help articles, banners, site notices |
| `cms_banner` | Home page banners |

### RBAC Domain

| Table | Description |
|-------|------------|
| `ums_admin` | Admin user accounts |
| `ums_role` | Role definitions |
| `ums_menu` | Admin sidebar menu tree |
| `ums_resource` | API permission resources |
| `ums_resource_category` | Resource category grouping |
| `ums_role_resource_relation` | Role-to-resource permissions |

### System Tables

| Table | Description |
|-------|------------|
| `checkpoints` | Agent plan state checkpoints |
| `llm_usage_logs` | LLM API call cost tracking |
| `trip_history` | Product view history |
| `refresh_tokens` | JWT refresh token storage |
| `plan_runs` | Agent plan execution records |
| `plan_run_events` | Agent runtime event log |

---

## Key Features Implemented

### Search & Discovery

- **Hybrid Search**: Elasticsearch full-text + pgvector semantic search with reranking
- **Autocomplete**: Real-time search suggestions as user types
- **Query Expansion**: Automatic query rewriting for better recall
- **Search Personalization**: User behavior-based search ranking
- **Trending Products**: Hot/new product detection and promotion

### AI Recommendations

- **Collaborative Filtering**: User-item interaction vectors for similarity-based recommendations
- **Product Embeddings**: Local HuggingFace model generates 384-dimensional embeddings
- **AB Testing**: Controlled experiment framework for testing recommendation strategies
- **Feature Engineering**: User and product feature extraction for ML pipelines
- **Metrics**: Business KPIs and model performance monitoring

### AI Agent (LangGraph)

- **Supervisor-Specialist Architecture**: Single supervisor routes to 6 domain specialists
- **Recommendation Subgraph**: 7-node recommendation pipeline (user profiling through marketing copy)
- **Tool System**: Registry pattern with Saga transaction support and audit tracing
- **LiteLLM Integration**: Multi-provider LLM gateway (DeepSeek, Kimi)

### Admin Panel

- **PMS**: Full product lifecycle management (CRUD, SKUs, attributes, categories, brands)
- **OMS**: Order management with status tracking and return processing
- **SMS**: Coupon and flash sale campaign management
- **CMS**: Content management for banners, notices, help articles
- **UMS**: Member and admin user management
- **RBAC**: Role-based access control with menu and resource permissions

### Customer Mall

- **Shopping Experience**: Browsing, search, product detail, cart, checkout, payment
- **Member Center**: Order history, favorites, addresses, coupons, profile
- **Real-time Features**: JWT auto-refresh, auth guards, cart persistence

### Infrastructure

- **Docker Compose**: 8-service deployment (PostgreSQL, Redis, Elasticsearch, LiteLLM, Marketplace, Agent Worker, Agent Beat, Mall Web)
- **Alembic Migrations**: Incremental schema versioning
- **Celery Tasks**: Async CF computation, search indexing, order processing
- **CI/CD**: GitHub Actions for lint, test, Docker build

---

## Statistics

| Metric | Count |
|--------|-------|
| **Backend API route files** | 32 (19 admin + 13 portal) |
| **Backend service files** | 21 |
| **Backend ORM model entities** | 30+ across 7 domains |
| **Database tables** | 30+ |
| **Agent specialist nodes** | 7 |
| **Agent recommendation nodes** | 7 |
| **Agent tool implementations** | 7 |
| **Admin frontend views** | 10 modules |
| **Customer mall views** | 21 pages |
| **Docker services** | 8 |
| **Celery task types** | 3 domains (CF, index, order) |
| **Monorepo packages** | 4 (backend, agent, shared, litellm) |
