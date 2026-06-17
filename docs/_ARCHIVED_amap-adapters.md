# 高德地图 API 工具链适配层 —— 开发总结

## 概述

为 SnapTrip Agent 项目集成高德地图（Amap）REST API，使 Agent 能够通过高德地图获取商家、娱乐场所等实时位置信息，进行路线规划与商家选择。遵循 **SOCID** 设计原则，建立了完整的适配器层、统一异常体系和三层测试金字塔。

---

## 一、新增文件清单

### 1.1 统一异常体系

| 文件 | 说明 |
|---|---|
| `backend/app/core/exceptions.py` | 16 个异常类，3 层继承树（SnapTripException → 业务异常 → 具体异常） |
| `backend/app/core/exception_handlers.py` | 10 个 FastAPI 全局异常 handler，含 trace_id 关联 + 结构化日志 |

### 1.2 高德适配层

| 文件 | 说明 |
|---|---|
| `backend/app/adapters/base.py` | `BaseAmapAdapter` 抽象基类，定义 `execute()` / `validate()` 契约 |
| `backend/app/adapters/amap_client.py` | `AmapApiClient` — HTTP 客户端（签名/鉴权/异常包装/重试） |
| `backend/app/adapters/registry.py` | `AdapterRegistry` + `AdapterRouter` — 工具名→适配器路由分发 |
| `backend/app/adapters/schemas/types.py` | `AmapStr` 类型 — 自动将高德 API 返回的 `[]` 转为 `""` |
| `backend/app/adapters/schemas/poi.py` | POI 搜索 / 详情 响应 Schema |
| `backend/app/adapters/schemas/route.py` | 步行 / 驾车 / 公交路径规划响应 Schema |
| `backend/app/adapters/schemas/geocode.py` | 地理编码 / 逆地理编码响应 Schema |
| `backend/app/adapters/schemas/district.py` | 行政区划查询响应 Schema |
| `backend/app/adapters/schemas/weather.py` | 天气查询响应 Schema |
| `backend/app/adapters/mappers/poi_mapper.py` | AmapPoiItem → 内部 POI Schema 转换器 |
| `backend/app/adapters/mappers/route_mapper.py` | AmapPath → 内部路由数据转换器 |
| `backend/app/adapters/mappers/geo_mapper.py` | 坐标格式转换工具函数集合 |
| `backend/app/adapters/adapters/poi_adapter.py` | POI 搜索适配器（周边搜索 / 关键字搜索） |
| `backend/app/adapters/adapters/route_adapter.py` | 路径规划适配器（步行 / 驾车 / 公交） |
| `backend/app/adapters/adapters/geocode_adapter.py` | 地理编码 + 逆地理编码适配器 |
| `backend/app/adapters/adapters/district_adapter.py` | 行政区划查询适配器 |

### 1.3 测试

| 文件 | 说明 |
|---|---|
| `tests/unit/adapters/test_mappers.py` | Mapper 单元测试（23 tests） |
| `tests/unit/adapters/test_amap_client.py` | Client 签名 / 超时 / 异常单元测试（11 tests） |
| `tests/unit/adapters/test_adapters.py` | 5 个 Adapter 单元测试（8 tests） |
| `tests/unit/adapters/test_registry.py` | Registry / Router 单元测试（11 tests） |
| `tests/contract/snapshots/amap_poi_search.json` | POI 搜索响应快照 |
| `tests/contract/snapshots/amap_route_walking.json` | 步行路径响应快照 |
| `tests/contract/snapshots/amap_geocode.json` | 地理编码响应快照 |
| `tests/contract/test_amap_schemas.py` | Schema 兼容性合约测试（13 tests） |
| `tests/integration/test_amap_integration.py` | 集成测试（12 tests） |

---

## 二、修改文件清单

| 文件 | 修改内容 |
|---|---|
| `backend/app/core/config.py` | 新增 7 个 AMAP_* 配置项 + `amap_enabled` property |
| `backend/app/main.py` | 注册 10 个全局异常 handler |
| `backend/pyproject.toml` | 新增 `respx` 测试依赖 + 6 个 pytest markers |
| `.env.example` | 新增 Amap 配置段 |
| `.github/workflows/ci.yml` | integration 测试加 `-m "not amap"` 过滤 |

---

## 三、解决的问题

### 3.1 配置层面

| 问题 | 解决方案 |
|---|---|
| `DATABASE_URL` 指向不存在的 `snaptrip` 库 | 改为实际 docker-compose 创建的 `snaptrip_dev` |
| `DATABASE_TEST_URL` 缺失 | 新增配置指向 `snaptrip_test` |
| `POSTGRES_DB` 与 docker-compose 不一致 | 改为 `snaptrip_dev` |

### 3.2 环境层面

| 问题 | 解决方案 |
|---|---|
| `ModuleNotFoundError: No module named 'fastapi'` | `uv sync --dev --reinstall` 重新安装依赖到 `.venv` |
| `.venv` 缺少 `pytest` | `uv pip install pytest pytest-asyncio pytest-cov respx ruff mypy` |
| Docker 容器名冲突 `snaptrip-db` | `docker rm -f snaptrip-db` 清理旧容器 |
| 数据库不存在 | `docker-compose up -d postgres redis` + 手动创建 test 库 |
| 表未创建 | `uv run alembic upgrade head` 执行迁移 |

### 3.3 Schema 层面

| 问题 | 解决方案 |
|---|---|
| 高德 API 空字段返回 `[]` 而非 `""`，Pydantic 解析失败 | 创建 `AmapStr` 类型（`Annotated[str, BeforeValidator(…)]`），全局应用 |
| 高德 API 返回额外未知字段 | 所有 Schema 添加 `model_config = ConfigDict(extra="ignore")` |
| `AMAP_BASE_URL` 含 `/v3` 导致请求 URL 出现 `/v3/v3/` | 改为 `https://restapi.amap.com`，路径中保留 `/v3/…` |

### 3.4 测试层面

| 问题 | 解决方案 |
|---|---|
| `os.getenv()` 不读 `.env` 文件，amap 集成测试始终被 skip | 改用 `settings.AMAP_API_KEY`（Pydantic Settings 自动读 `.env`） |
| `@pytest.mark.amap` 没有 skip 效果 | 替换为 `@pytest.mark.skipif(…)` |
| CI 环境无 Amap Key 导致测试失败 | CI workflow 加 `-m "not amap"` 跳过真实 API 测试 |

---

## 四、架构设计

```
Agent Pipeline
  ↓ ToolInvocation
AdapterRouter.dispatch(tool_name)
  ├─ AMAP_TOOL + Key存在  → AmapAdapter.execute()  → AmapApiClient  → 高德 REST API
  ├─ AMAP_TOOL + Key缺失  → degraded               → Mock Server 降级
  └─ MOCK_TOOL            → MockGateway.call()       → Mock Server
```

### SOCID 原则体现

| 原则 | 实现 |
|---|---|
| **S**eparation | Client（HTTP）/ Mapper（转换）/ Adapter（编排）三层独立 |
| **O**pen/Closed | 新增 API 只需加 Adapter + Schema + Mapper，不改现有代码 |
| **C**onsistent Exception | 15 个异常类统一继承 `SnapTripException`，全局 handler 统一响应格式 |
| **I**nterface Segregation | `BaseAmapAdapter` 仅定义 `execute()` 一个核心方法 |
| **D**ependency Inversion | ToolDAGExecutor 依赖 `AdapterRouter` 接口，不依赖具体实现 |

### 异常层级

```
SnapTripException
├── ValidationError / AuthenticationError / PermissionDeniedError / ResourceNotFoundError
├── AgentError → IntentParseError / PlanningError / ExecutionError
├── AdapterError → AmapApiError / AmapAuthError / AmapRateLimitError / AdapterTimeoutError
├── GatewayError → MockApiError / LLMError
└── CircuitBreakerOpenError
```

### 高德 API 覆盖

| 工具名 | 高德 API | 用途 |
|---|---|---|
| `search_poi` | `/v3/place/text` `/v3/place/around` | 周边 / 关键字 POI 搜索 |
| `calculate_route` | `/v3/direction/walking` 等 | 步行 / 驾车 / 公交路径规划 |
| `geocode_address` | `/v3/geocode/geo` | 地址 → 坐标 |
| `reverse_geocode` | `/v3/geocode/regeo` | 坐标 → 地址 |
| `search_district` | `/v3/config/district` | 行政区划查询 |

---

## 五、测试结果

### 本地全量测试（含真实高德 API）

```
72 passed (单元 53 + 合约 13 + 集成 6 CI + 集成 6 Amap)
```

### CI 测试（不含真实高德 API）

```
pytest tests/ -m "not amap" -v
```

### 测试运行命令

```bash
# 全部测试（CI 模式）
uv run pytest tests/ -m "not amap" -v

# 高德真实 API 测试（需配置 AMAP_API_KEY）
uv run pytest tests/integration/test_amap_integration.py -v

# 合约快照测试
uv run pytest tests/contract/ -v

# 单元测试
uv run pytest tests/unit/adapters/ -v
```
