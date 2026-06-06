# SnapTrip 后端开发阶段总结文档

> 版本: 0.2.0 | 日期: 2026-05-18

---

## 目录

1. [子任务 1：数据库模型与 Alembic 迁移](#1-数据库模型与-alembic-迁移)
2. [子任务 2：Redis 服务封装与 Celery 配置](#2-redis-服务封装与-celery-配置)
3. [子任务 3：认证系统](#3-认证系统)
4. [子任务 4：用户中心 API](#4-用户中心-api)
5. [子任务 5：LLM 网关](#5-llm-网关)
6. [子任务 7：工具层 Schema 定义](#7-工具层-schema-定义)
7. [子任务 8：Mock Server 实现](#8-mock-server-实现)
8. [子任务 9：DAG 调度与熔断器](#9-dag-调度与熔断器)
9. [子任务 10：Docker Compose 部署配置](#10-docker-compose-部署配置)
10. [子任务 11：测试与 CI](#11-测试与-ci)
11. [高德地图 API 适配层设计](#高德地图-api-适配层设计)

---

## 1. 数据库模型与 Alembic 迁移

### 实现功能

| 产出 | 说明 |
|------|------|
| `app/models/` 9 个模型文件 | SQLAlchemy 2.0 声明式语法（`Mapped` / `mapped_column`），UUID 主键 |
| `app/db/session.py` | `async_engine` + `AsyncSessionLocal` + `get_db()` FastAPI 依赖 |
| `app/core/config.py` | Pydantic-Settings 统一配置，禁止 `os.getenv` 散落 |
| `alembic/` 目录 | async 模式 `env.py` + `8da6e575b9c0_init.py` 初始迁移 |
| `backend/init.sql` | `CREATE EXTENSION vector; CREATE EXTENSION btree_gin;` |

### 数据表清单

| 表名 | 用途 | 关键字段 |
|------|------|---------|
| `users` | 用户账户 | email (unique), hashed_password, oauth_provider |
| `user_profiles` | 用户画像 | preferences (JSONB), preference_embedding (Vector 1536) |
| `plans` | 活动计划 | status (draft/planning/confirmed/cancelled), date_range (DATERANGE), group_type |
| `plan_slots` | 计划时段 | slot_status (locked/tentative/cancelled), booking_ref |
| `checkpoints` | 计划快照 | slots_snapshot (JSONB), consensus_status |
| `plan_adjustments` | 变更记录 | original_slots / adjusted_slots (JSONB) |
| `pois` | 兴趣点 | embedding (Vector 1536), group_suitability (JSONB) |
| `llm_usage_logs` | LLM 调用日志 | model_name, prompt_tokens, completion_tokens, latency_ms |
| `refresh_tokens` | 刷新令牌 | token_hash (SHA256), expires_at |

### 索引设计

- `users.email`：唯一 B-tree
- `plans(user_id, status)`：复合 B-tree
- `plan_slots(plan_id, time_start)`：复合 B-tree
- `pois(lat, lng)`：B-tree
- `pois.embedding`：HNSW（m=16, ef_construction=64）
- `pois.category`：B-tree

### 解决的问题

- 建立完整的持久化基础，所有业务模型有对应的数据库表
- pgvector HNSW 索引支持高性能语义向量检索（1536 维）
- Alembic 支持 `--autogenerate` 增量迁移，`alembic upgrade head` 自动建表
- 严格遵循项目约束：禁止 SQLAlchemy 1.x 风格、FK 全量 `relationship`、UTC 时间戳

---

## 2. Redis 服务封装与 Celery 配置

### 实现功能

| 产出 | 说明 |
|------|------|
| `MemoryService` 重写 | 从 in-memory dict → `redis.asyncio` 完整实现 |
| `app/celery_app.py` | Celery 应用实例，Redis broker + backend，JSON 序列化 |
| `app/tasks/plan_tasks.py` | 3 个异步任务：`create_plan_async` / `notify_share_card` / `rebuild_user_preference_embedding` |

### MemoryService 接口

| 接口 | 功能 | Redis 数据结构 |
|------|------|--------------|
| `set_session_state` / `get_session_state` | 会话状态读写 | String (TTL) |
| `push_dialogue` / `get_dialogue` | 对话历史 | List (FIFO + ltrim) |
| `set_hot_pois` / `get_hot_pois` | 热门 POI 缓存 | String (JSON, TTL) |
| `sliding_window_check` | 滑动窗口限流 | Sorted Set |
| `set_transaction_status` / `get_transaction_status` | 事务状态 | String (TTL) |

### 解决的问题

- Agent 不直接操作 Redis，全部通过 MemoryService 解耦
- 滑动窗口限流支持 IP 级（100 req/min）和用户级（300 req/min）
- Celery Worker 独立进程处理耗时任务（偏好向量重建、分享卡片），不阻塞 API 响应
- 生产可切换 Redis Cluster / Sentinel，无需修改业务代码

---

## 3. 认证系统

### 实现功能

| 产出 | 说明 |
|------|------|
| `app/core/security.py` | bcrypt 密码哈希、JWT HS256 签发/验证、`get_current_user` 依赖 |
| `app/core/response.py` | `APIException` + `success()`/`error()` 统一响应 + 全局异常处理器 |
| `app/core/rate_limit.py` | IP/用户双层限流，白名单 `/auth/*` `/health` `/docs` |
| `app/api/v1/auth.py` | 5 端点：register / login / refresh / logout / me |
| `app/schemas/auth.py` | Pydantic 模型：`RegisterRequest` / `LoginRequest` / `TokenResponse` |

### API 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/v1/auth/register` | POST | Email + password 注册，自动创建 user_profiles |
| `/api/v1/auth/login` | POST | 验证密码，颁发 access (15min) + refresh (7d) 双 token |
| `/api/v1/auth/refresh` | POST | refresh token 轮换，旧 token 立即失效（防重放） |
| `/api/v1/auth/logout` | POST | 删除 refresh_token，access token 自然过期 |
| `/api/v1/auth/me` | GET | 返回 id/email/nickname/avatar_url（JOIN user_profiles） |

### 安全特性

- 密码 bcrypt 哈希（salt rounds = 12），禁止明文存储
- `JWT_SECRET_KEY` 从环境变量读取，禁止硬编码
- refresh token SHA256 哈希后存 PG，原始值仅返回一次
- 统一异常处理：ValidationError / HTTPException / APIException 包装为 `{code, message, data}`

### 解决的问题

- 完整的认证闭环：注册 → 登录 → 访问 → 刷新 → 登出
- 限流中间件保护 API 端点，白名单跳过认证路由
- 全局异常处理器实现统一错误格式，前端无需处理多种错误结构

---

## 4. 用户中心 API

### 实现功能

| 产出 | 说明 |
|------|------|
| `app/api/v1/user.py` | 5 端点：profile CRUD / plans 分页 / plan 详情 / plan 克隆 |
| `app/services/user_service.py` | `trigger_preference_embedding_update()` Celery 触发 |
| `app/schemas/user.py` | `UserProfileOut` / `PlanListOut` / `PlanDetailOut` / `PaginatedPlans` |

### API 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/v1/user/profile` | GET | 完整资料（preferences / embedding / travel_style / home_address） |
| `/api/v1/user/profile` | PUT | 更新资料，preferences 变更时自动触发 Celery 向量重建 |
| `/api/v1/user/plans` | GET | 分页查询（page_size 最大 100），支持 status / group_type 过滤 |
| `/api/v1/user/plans/{plan_id}` | GET | 嵌套详情（`selectinload` slots + checkpoints + adjustments） |
| `/api/v1/user/plans/{plan_id}/clone` | POST | 原子性复制 plan + 全部 slots 为 draft |

### 关键设计

- 所有路由注入 `get_current_user`，禁止跨用户查询
- `selectinload` 避免 N+1 查询（Plan → PlanSlot / Checkpoint / PlanAdjustment）
- 克隆操作在一个 DB 事务中完成（slots 重置为 tentative / booking_ref=null）
- 偏好向量 Celery 任务优雅降级（Worker 未启动时不抛异常）

### 解决的问题

- 用户资料持久化与偏好向量异步更新
- 计划历史查询支持多条件过滤 + 分页
- 计划克隆实现"模板复用"场景，原子性保证数据一致性

---

## 5. LLM 网关

### 实现功能

| 产出 | 说明 |
|------|------|
| `app/services/llm_gateway.py` | `LLMGateway` 类：chat / embed + 降级链 + Token 统计 |

### 核心接口

| 方法 | 说明 | 返回 |
|------|------|------|
| `chat(messages, model_alias, max_tokens, temperature, timeout)` | 聊天补全 + 自动降级 | `{content, model, usage}` |
| `embed(texts, model, timeout)` | 文本 Embedding | `[[1536维向量], ...]` |

### 降级链

```
deepseek/deepseek-v3 (主模型, 5s timeout)
        ↓ 失败
google/gemma-3-4b-it:free (备用, 0.5s 间隔)
```

### Token 统计

每次调用自动写入 `llm_usage_logs` 表：
- `model_name`：实际调用的模型
- `prompt_tokens` / `completion_tokens`：token 消耗
- `latency_ms`：响应延迟
- `endpoint`：chat / embedding

### 模型别名

| 别名 | 实际模型 |
|------|---------|
| `deepseek` | `deepseek/deepseek-v3` |
| `deepseek-r1` | `deepseek/deepseek-r1` |
| `gemma` | `google/gemma-3-4b-it:free` |

### 解决的问题

- 统一 LLM 调用入口，Agent 不再散落 httpx 直调
- 自动降级保障可用性：主模型故障时无需人工干预
- Token 成本可审计，`llm_usage_logs` 表支撑成本分析和配额预警

---

## 7. 工具层 Schema 定义

### 实现功能

| 产出 | 说明 |
|------|------|
| `app/schemas/tool.py` | `ToolInvocation` / `ToolResult` / `ToolDefinition` + 10 工具注册表 |

### Schema 对照（旧 → 新）

| 旧字段 | 新字段 | 说明 |
|--------|--------|------|
| `ToolInvocation.node_id` | `invocation_id: str` (UUID) | 链路追踪 |
| `ToolInvocation.slot_index` | 移入 `params["slot_index"]` | 参数化 |
| `ToolResult.success: bool` | `status: Literal["success","failure","timeout","degraded"]` | 4 态枚举 |
| `ToolResult.elapsed_ms` | `latency_ms` | 语义化命名 |
| `ToolMeta` | `ToolDefinition` | 新增 `input_schema` / `output_schema` / `description` / `fallback_policy` |

### 10 工具注册表

| 工具 | Layer | 依赖 | Fallback | 说明 |
|------|-------|------|----------|------|
| `search_poi` | L0 | - | degrade | POI 搜索 |
| `get_user_profile` | L0 | - | degrade | 用户画像 |
| `check_queue` | L1 | search_poi | degrade | 排队查询 |
| `check_availability` | L1 | search_poi | degrade | 可用时段 |
| `check_child_facility` | L1 | search_poi | degrade | 亲子设施 |
| `calculate_route` | L1 | search_poi | degrade | 路线规划 |
| `book_table` | L2 | check_queue, check_availability | abort | 预订桌位 |
| `book_ticket` | L2 | check_availability | degrade | 预订门票 |
| `order` | L2 | search_poi | continue | 下单 |
| `notify` | L3 | book_table, book_ticket, order | continue | 通知 |

### 三个 Fallback 策略

| 策略 | 行为 |
|------|------|
| `abort` | 失败后终止后续所有层（关键操作，如预订） |
| `degrade` | 失败后标记降级但继续执行（查询类操作） |
| `continue` | 失败后忽略，继续下一层（通知类操作） |

### 解决的问题

- Hermes Agent 兼容协议，每个工具含 JSON Schema 可用于前端参数校验
- 4 态结果（success / failure / timeout / degraded）覆盖所有执行场景
- `fallback_policy` 实现差异化降级：预订失败应终止，查询失败可继续

---

## 8. Mock Server 实现

### 实现功能

| 产出 | 说明 |
|------|------|
| `mock_server/app/main.py` | 独立 FastAPI 实例，端口 8001 |
| `mock_server/app/schemas.py` | 统一 `ToolResult` 响应模型 |
| `mock_server/app/core/fault.py` | 5% 503 + 10% 1-3s 延迟故障注入 |
| `mock_server/data/seed_pois.json` | 20 条 POI，覆盖北京/上海/重庆，8 个类别 |
| 6 个 Router 文件 | poi / queue / order / route / weather / delivery |

### Mock 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/health` | GET | 健康检查 |
| `/poi/search` | GET | POI 搜索（Haversine 距离 + keyword/category/group_type 过滤） |
| `/poi/queue` | GET | 排队查询（随机 wait_minutes, available_slots） |
| `/order/prepare` | POST | 下单准备（prepare_id, 15min 有效期） |
| `/order/submit` | POST | 提交订单（prepare → confirmed） |
| `/order/pay` | POST | 支付（90% 成功, 10% PAYMENT_FAILED） |
| `/route` | GET | 路线规划（walk/drive/transit + polyline） |
| `/weather` | GET | 天气（温度/湿度/空气质量/户外适宜） |
| `/delivery/schedule` | POST | 配送调度 |

### 故障模拟

- 5% 概率返回 HTTP 503 + `error_code: SERVICE_UNAVAILABLE`
- 10% 概率注入 1-3s 随机延迟
- 所有响应包装为 `{status, data, error_code, error_message, latency_ms}`

### 订单状态机

```
prepare ──submit──→ confirmed ──pay──→ paid
   │ (expired)          │ (invalid)
   ↓                    ↓
 失败 (PREPARE_EXPIRED)  失败 (INVALID_ORDER_ID / PAYMENT_FAILED)
```

### 解决的问题

- 开发阶段无需接入美团真实 API，Mock Server 提供完整模拟
- 故障注入让 Fallback Engine 在开发阶段就能测试降级逻辑
- 独立部署（Dockerfile + uvicorn），backend 通过 httpx 调用

---

## 9. DAG 调度与熔断器

### 实现功能

| 产出 | 说明 |
|------|------|
| `app/services/tool_dag.py` | `ToolDAGExecutor`（拓扑排序 → httpx → Mock Server）+ `ToolDAGScheduler`（兼容旧接口） |
| `app/services/circuit_breaker.py` | 三态熔断器：CLOSED → OPEN → HALF_OPEN |
| `app/services/saga.py` | `SagaCoordinator`：步骤记录 + 逆序补偿 |

### ToolDAGExecutor 执行流程

```
输入: [ToolInvocation, ...]
  │
  ├── 拓扑排序分层 (topological_layers)
  │     ├── L0: search_poi, get_user_profile  (并行)
  │     ├── L1: check_queue, check_availability, ... (并行)
  │     ├── L2: book_table, book_ticket, order (并行)
  │     └── L3: notify
  │
  ├── 逐层并行执行 (asyncio.gather)
  │     └── 每节点: CircuitBreaker.call(httpx → Mock Server)
  │
  ├── Redis 持久化: txn:{id}:step:{invocation_id}
  │
  └── fallback_policy 决策:
        ├── abort → 终止后续层
        ├── degrade → 继续 + 标记降级
        └── continue → 忽略失败继续
```

### 熔断器状态机

```
CLOSED ──failure_threshold (5)──→ OPEN ──recovery_timeout (30s)──→ HALF_OPEN
   ↑                                                                   │
   └──────────────── success (重置计数器) ─────────────────────────────┘
```

### Saga 协调器

| 方法 | 说明 |
|------|------|
| `register_compensation(tool_name, fn)` | 注册补偿函数 |
| `record_step(invocation, result)` | 记录已完成步骤 |
| `compensate()` | 逆序执行补偿，单步失败继续剩余补偿 |

### 解决的问题

- DAG 分层并行执行：无依赖节点同层并发，提升执行效率
- 循环依赖检测：拓扑排序阶段即发现并拒绝非法 DAG
- 熔断保护：工具连续失败自动熔断，防止雪崩（book_table 20% 失败率模拟）
- Saga 补偿：非幂等操作（预订/下单）失败时可回滚已完成步骤
- Redis 追踪：`txn:{id}:step:{invocation_id}` 支持执行进度查询

---

## 10. Docker Compose 部署配置

### 实现功能

| 产出 | 说明 |
|------|------|
| `docker-compose.yml` | 6 服务编排 + 健康检查 + 自动迁移 |
| `docker-compose.override.example.yml` | 开发环境热重载覆盖 |
| `backend/init.sql` | 自动创建 vector + btree_gin 扩展 |
| `.env.example` | 完整环境变量模板 |

### 服务清单

| 服务 | 镜像 | 端口 | 健康检查 | 说明 |
|------|------|------|---------|------|
| `postgres` | pgvector/pgvector:pg16 | 5432 | `pg_isready` | 自动加载 init.sql |
| `redis` | redis:7-alpine | 6379 | `redis-cli ping` | 缓存 + Celery broker |
| `backend` | `./backend` build | 8000 | `curl /health` | 启动时 `alembic upgrade head` |
| `mock-server` | `./mock_server` build | 8001 | `curl /health` | 故障注入中间件 |
| `celery-worker` | `./backend` build | - | - | 复用 backend 镜像 |
| `frontend` | `./frontend` build | 5173 | - | Vite dev server |

### 解决的问题

- 一键启动：`docker compose up -d` 启动全部 6 个服务
- 自动迁移：backend 容器启动时执行 `alembic upgrade head`
- 容器网络内通信：`DATABASE_URL=...@postgres:5432/...` `/ REDIS_URL=redis://redis:6379/0`
- Production / Development 双模式（`BUILD_TARGET` + override）

---

## 11. 测试与 CI

### 实现功能

| 产出 | 说明 |
|------|------|
| `tests/conftest.py` | 14 个共享 fixtures（POI / Intent / Slot / Draft / StateMachine） |
| 11 个单元测试文件 | 118 个测试用例 |
| 3 个集成测试文件 | 14 个测试用例 |
| 1 个契约测试文件 | 8 个测试用例（需 Mock Server 运行） |
| `.github/workflows/ci.yml` | 4 个 job：lint-backend / lint-frontend / test-backend / docker-build |
| `Makefile` | `test-unit` / `test-integration` 分离运行 |

### 测试覆盖

| 测试文件 | 覆盖范围 | 用例数 |
|----------|---------|--------|
| `test_auth.py` | 密码哈希、JWT 签发/验证、refresh token | 7 |
| `test_user.py` | ProfileOut / PlanListOut / PlanSlotOut Schema | 3 |
| `test_intent_parser.py` | 关键词解析：城市/类型/心情/预算/场景 | 12 |
| `test_state.py` | FSM 守卫 + 跃迁 + 超时 | 22 |
| `test_planning_engine.py` | Phase1/2 过滤排序 + 时段生成 | 11 |
| `test_execution_engine.py` | DAG 执行结果 + 状态分类 | 2 |
| `test_fallback_engine.py` | 涟漪重排 + Shadow 替换 + Diff | 6 |
| `test_retrieval_engine.py` | Haversine 距离 | 4 |
| `test_tool_dag.py` | 工具注册 + 分层 + 熔断 + 拓扑排序 | 11 |
| `test_dag.py` | 三态熔断 + 拓扑分层 + Saga 补偿 | 13 |
| `test_memory_service.py` | Redis 9 个接口 | 10 |
| `test_llm_gateway.py` | 模型别名 + 降级链 + LLMError | 8 |
| `test_vector_service.py` | Embedding 维度 + 降级链 | 7 |
| `test_mock_server.py` | Mock 端点契约（需 localhost:8001） | 8 |

### 集成测试

| 测试文件 | 覆盖范围 | 用例数 |
|----------|---------|--------|
| `test_auth_api.py` | 注册→登录→刷新→登出→me 全流程 | 4 |
| `test_user_api.py` | Profile CRUD + Plans 分页 | 4 |
| `test_plan_api.py` | Plan Create + Get + SSE 流 | 4 |
| `test_api.py` | E2E 注册→资料→计划→SSE | 2 |

### CI 流水线

```
push/PR
  ├── lint-backend (ruff + mypy)     ─┐
  ├── lint-frontend (tsc --noEmit)    ├─ 并行
  ├── test-backend                    │
  │     ├── Unit tests (118)          │
  │     ├── Integration tests (14)     │
  │     └── Coverage upload (Codecov) │
  └── docker-build (3 images)        ─┘
```

### 已知限制

- 集成测试需 PostgreSQL + Redis，与单元测试不能混合运行（asyncpg 事件循环冲突）
- CI 和 Makefile 已将单测/集成测分离执行，本地开发使用 `make test-unit` / `make test-integration`

---

## 高德地图 API 适配层设计

### 分层架构

```
┌──────────────────────────────────────────────────────┐
│  Layer 1: amap_gateway.py                            │
│    httpx → 高德 Web API (/v3/place /v3/direction)   │
│    统一签名、超时、错误处理                            │
├──────────────────────────────────────────────────────┤
│  Layer 2: amap_adapter.py                            │
│    高德 JSON → SnapTrip POI Schema 转换              │
│    类别映射 (typecode → restaurant/cafe/attraction)   │
├──────────────────────────────────────────────────────┤
│  Layer 3: Tool Schema (schemas/tool.py)               │
│    新增 3 工具: amap_search_poi / route / weather    │
│    更新现有 10 工具依赖关系                            │
├──────────────────────────────────────────────────────┤
│  Layer 4: Agent 适配                                  │
│    RetrievalEngine: SEED_POIS → amap_search_poi      │
│    PlanningEngine: Haversine → amap_route            │
│    新增 weather 注入 context                          │
├──────────────────────────────────────────────────────┤
│  Layer 5: 降级策略                                    │
│    API 超时 → SEED_POIS + Haversine                  │
│    API Key 未配置 → 跳过，使用 mock                   │
│    配额耗尽 → Redis 缓存 (TTL 1h)                     │
└──────────────────────────────────────────────────────┘
```

### 新增 Tool 注册

| 工具 | Layer | 依赖 | 高德 API |
|------|-------|------|---------|
| `amap_search_poi` | L0 | - | `/v3/place/text` / `/v3/place/around` |
| `amap_route` | L1 | amap_search_poi | `/v3/direction/{mode}` |
| `amap_weather` | L0 | - | `/v3/weather/weatherInfo` |

### 数据适配映射

| 高德字段 | SnapTrip POI 字段 |
|----------|------------------|
| `id` | `id` |
| `name` | `name` |
| `location` (lng,lat) | `lng`, `lat` |
| `typecode` | `type` (通过映射表) |
| `biz_ext.rating` | `rating` |
| `biz_ext.cost` | `avg_price` |
| `biz_ext.open_time` | `business_hours` |
| `deep_info.child` | `child_friendly` |

### 配置

```python
AMAP_API_KEY: str = ""                  # 高德 Web API Key
AMAP_API_BASE_URL: str = "https://restapi.amap.com/v3"
AMAP_TIMEOUT: int = 3
AMAP_CACHE_TTL: int = 3600
```

---

## 架构全景

```
┌──────────────────────────────────────────────────────────────┐
│                      FastAPI (main.py)                       │
│           lifespan: hub + memory + mock_gateway              │
├──────────────────────────────────────────────────────────────┤
│  API v1                                                      │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌──────────┐          │
│  │  auth   │ │  plan   │ │  user   │ │ session  │          │
│  │ 5 routes│ │ 3 routes│ │ 5 routes│ │   SSE    │          │
│  └─────────┘ └─────────┘ └─────────┘ └──────────┘          │
├──────────────────────────────────────────────────────────────┤
│  9 Agents (同进程内存 AgentContext/AgentResult 传递)          │
│  IntentParser → ContextLoader → MemoryManager               │
│  → RetrievalEngine → PlanningEngine                         │
│  → ConsensusResolver → ExecutionEngine                      │
│  → FallbackEngine → NotifyEngine                            │
├──────────────────────────────────────────────────────────────┤
│  Services                                                    │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────────┐     │
│  │ LLMGateway   │ │MemoryService │ │ToolDAGExecutor   │     │
│  │ (OpenRouter) │ │   (Redis)    │ │(httpx→Mock:8001) │     │
│  ├──────────────┤ ├──────────────┤ ├──────────────────┤     │
│  │MockAPIGateway│ │CircuitBreaker│ │SagaCoordinator   │     │
│  ├──────────────┤ ├──────────────┤ ├──────────────────┤     │
│  │ UserService  │ │  PlanService │ │  LLMGateway      │     │
│  └──────────────┘ └──────────────┘ └──────────────────┘     │
├──────────────────────────────────────────────────────────────┤
│  Data                                                        │
│  ┌──────────────────┐  ┌──────────────────┐                 │
│  │ PostgreSQL 16    │  │    Redis 7       │                 │
│  │ + pgvector       │  │ (cache / queue)  │                 │
│  │ 9 tables         │  │                  │                 │
│  └──────────────────┘  └──────────────────┘                 │
├──────────────────────────────────────────────────────────────┤
│  Async (Celery Worker)                                       │
│  rebuild_preference_embedding / create_plan / notify         │
├──────────────────────────────────────────────────────────────┤
│  External                                                    │
│  ┌──────────────────┐  ┌──────────────────┐                 │
│  │  Mock Server     │  │   OpenRouter     │                 │
│  │  (port 8001)     │  │  (DeepSeek-V3)   │                 │
│  │  6 endpoints     │  │  + gemma fallback │                 │
│  └──────────────────┘  └──────────────────┘                 │
└──────────────────────────────────────────────────────────────┘
```

---

## 数据模型 ER

```
users ──1:N──→ plans ──1:N──→ plan_slots
  │              │
  │              ├──1:N──→ checkpoints
  │              │
  │              └──1:N──→ plan_adjustments
  │
  ├──1:1──→ user_profiles (Vector 1536)
  │
  └──1:N──→ refresh_tokens

pois (Vector 1536 + HNSW index)
llm_usage_logs
```

---

## 关键决策记录

| 决策 | 原因 | 影响 |
|------|------|------|
| Agent 通信同进程内存传递 | Hackathon 规模无需序列化 | 零开销，不能跨进程 |
| 全局 `async_engine` | 简化连接管理 | 集成测试需分离运行 |
| Refresh token 轮换 | 每次刷新作废旧 token | 防重放攻击 |
| Mock Server 故障注入 5% | 模拟生产不稳定性 | Fallback Engine 可验证 |
| DAG 拓扑排序 + 循环检测 | 保证执行顺序正确 | 拒绝非法 DAG |
| HNSW 索引 m=16 ef_construction=64 | pgvector 推荐配置 | 查询速度与构建成本平衡 |
| 集成测试与单元测试分离 | pytest-asyncio + asyncpg 事件循环冲突 | Makefile 分离命令 |
| bcrypt 替代 passlib | passlib 与新版本 bcrypt 不兼容 | 直接使用 bcrypt 库 |
| 3 种 fallback_policy | 不同操作需要不同降级策略 | 预订 abort / 查询 degrade / 通知 continue |

---

## 统计总览

| 指标 | 数值 |
|------|------|
| Python 源文件 | 45+ |
| API 端点 | 18 |
| 数据库表 | 9 |
| Agent | 9 |
| Tool 注册 | 10 |
| Redis 接口 | 9 |
| Mock 端点 | 9 |
| Celery 任务 | 3 |
| Docker 服务 | 6 |
| CI Job | 4 |
| 单元测试 | 118 |
| 集成测试 | 14 |
| 契约测试 | 8 |
