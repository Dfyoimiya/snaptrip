# SnapTrip —— AI 驱动的全栈电商平台

> 基于 FastAPI + LangGraph + Vue 3 的全栈电商平台，集成 AI 智能搜索、个性化推荐与多智能体客服

**一句话描述**：商品浏览 → 混合搜索 → 购物车 → 下单支付 → AI 智能客服售后，全链路 AI 赋能

## 产品架构

```
用户端 (C 端)                    管理端 (B 端)
  ├── 首页聚合                    ├── 商品管理 (PMS)
  ├── 混合搜索 (ES+向量+CF)       ├── 订单管理 (OMS)
  ├── 商品详情 / 品牌 / 分类      ├── 会员管理 (UMS)
  ├── 购物车 / 下单 / 支付        ├── 促销管理 (SMS)
  ├── 个人中心 / 收藏 / 地址      ├── 内容管理 (CMS)
  ├── 个性化推荐 (AI)             ├── RBAC 权限
  └── 智能客服 (AI Agent)         └── AI 数据分析助手
```

## 技术栈

| 层级 | 技术 |
|------|------|
| AI Agent 框架 | LangGraph (StateGraph + Supervisor-Specialist 多智能体) |
| LLM 网关 | LiteLLM Proxy (DeepSeek-V4 / Kimi K2 多模型路由) |
| 后端 | FastAPI + Pydantic v2 + SQLAlchemy 2.0 async |
| 异步任务 | Celery + Redis |
| 数据库 | PostgreSQL 16 + pgvector (向量检索) |
| 搜索引擎 | Elasticsearch 8 |
| 缓存/消息 | Redis 7 (Session / PubSub / Rate Limit) |
| B 端前端 | Vue 3 + TypeScript + Element Plus + Vite |
| C 端前端 | Vue 3 + TypeScript + Tailwind CSS + Vite |
| 包管理 | uv workspace (Python monorepo) |
| 部署 | Docker Compose (8 服务) |

## 快速开始

### 前置要求

- Docker Desktop 4.x+
- Python 3.13+
- Node.js 20+
- uv (Python 包管理器)

### 一键启动

```bash
# 1. 克隆项目
git clone <repo-url> && cd snaptrip

# 2. 初始化（复制 .env、安装依赖）
make init

# 3. 启动全栈
make dev
```

### 服务端口

| 服务 | 端口 | 说明 |
|------|------|------|
| Marketplace API | 8000 | FastAPI 后端，Swagger: http://localhost:8000/docs |
| Admin 前端 | 5173 | B 端管理后台 |
| Mall Web | 5175 | C 端购物网站 |
| LiteLLM Proxy | 4000 | LLM API 网关 |
| PostgreSQL | 5432 | 数据库 + pgvector |
| Redis | 6379 | 缓存 / 消息队列 |
| Elasticsearch | 9200 | 全文搜索 |

### 开发命令

```bash
make backend-dev     # 后端热重载
make frontend-dev    # 管理后台热重载
make mall-web-dev    # 商城热重载
make test            # 运行全部测试
make test-unit       # 单元测试 + 覆盖率
make lint            # 代码检查 (ruff + mypy)
make format          # 代码格式化
make migrate         # 生成数据库迁移
make migrate-up      # 执行迁移
make seed            # 填充开发数据
```

## 项目结构

```
snaptrip/
├── backend/              # FastAPI 后端
│   ├── app/
│   │   ├── api/admin/    # 管理后台路由 (18 个模块)
│   │   ├── api/portal/   # 前台商城路由 (15 个模块)
│   │   ├── models/       # ORM 模型 (40+ 表, 6 大域)
│   │   ├── schemas/      # Pydantic 请求/响应
│   │   ├── services/     # 业务逻辑 (25+ 服务)
│   │   ├── search/       # Elasticsearch 客户端
│   │   ├── tasks/        # Celery 异步任务
│   │   └── core/         # 配置/安全/异常
│   ├── alembic/          # 数据库迁移
│   └── tests/            # 单元 + 集成测试
├── agent/                # AI Agent 引擎 (LangGraph)
│   └── src/agent/
│       ├── graph.py      # 主图编排 (Supervisor + 6 Specialist)
│       ├── nodes/        # 节点实现 + 推荐子图
│       ├── tools/        # 工具系统 (20 个工具 + Hook + Saga)
│       ├── adapters/     # LLM 适配器 (模型降级链)
│       ├── events/       # Redis Pub/Sub 事件总线
│       └── services/     # Agent 服务封装
├── shared/               # 共享库
│   └── snaptrip_shared/  # core (config/exceptions/security) + db
├── contracts/            # 接口契约 (Ports + Shared DTOs)
├── frontend/             # B 端管理后台 (Vue 3 + Element Plus)
├── mall-web/             # C 端购物网站 (Vue 3 + Tailwind)
├── litellm/              # LiteLLM 代理配置 (4 模型)
├── nginx/                # Nginx 反向代理
├── docker-compose.yml    # 8 服务编排
└── Makefile
```

## 核心特性

### 搜索与发现
- **三路混合搜索**：ES BM25 关键词 + pgvector 语义向量 (384d) + CF 协同过滤 (64d)，分数归一化 + 个性化 boost
- **实时搜索建议**：autocomplete 前缀补全 + trending 热词 + AI 建议，三区块并发聚合
- **查询扩展**：LLM 离线查询扩展 + Redis 缓存，提升头部查询召回率
- **个性化排序**：类目偏好 +0.15~0.20，价格匹配 +0.10，行为加权

### AI 推荐
- **4-Agent 推荐流水线**：UserProfile → ProductRec (召回+重排) → Inventory (库存过滤) → MarketingCopy (文案生成)
- **协同过滤**：ALS 隐因子模型 (64d)，行为加权 (view=1, purchase=5)，每 6 小时自动训练
- **A/B 测试**：MD5 一致性哈希分桶 + Thompson Sampling 动态分配

### AI 智能客服
- **Supervisor-Specialist 多智能体**：1 个 Supervisor 意图分类 + 6 个 Specialist 专业处理
- **情感感知**：5 种情感检测 (愤怒/沮丧/焦虑/满意/中性) + 多轮情感轨迹 + 动态调整语气
- **全场景售后**：退货资格校验 → 提交退货 → 退款进度 → 物流查询 → 投诉验证 → 工单管理 → 补偿发券
- **SLA 监控**：critical 15min / urgent 1h / normal 4h，超时告警 + 客服通知
- **合规检查**：PII 扫描 (手机号/邮箱/身份证/银行卡) + 禁用词检测，非阻断式

### Agent 工具系统
- **ToolHarness 统一入口**：Hook 链 (Auth → RateLimit → Trace → Audit → Alert)
- **Saga 事务**：Reserve → Confirm → Rollback 三阶段 + LIFO 补偿栈
- **防篡改审计**：SHA-256 哈希链，支持完整性验证
- **模型降级**：4 级降级链 (deepseek-v4-pro → v4-flash → kimi-k2.6 → k2.5) + 指数退避重试

### 平台能力
- **商品管理**：SPU + SKU + EAV 属性体系，品牌/分类树形管理
- **订单全生命周期**：待付款 → 已付款 → 已发货 → 已收货 → 已完成，乐观锁库存扣减
- **促销系统**：优惠券模板/领取/核销 + 秒杀活动/场次/商品三层管理
- **RBAC 权限**：角色 → 菜单 → 资源 → 管理员 完整体系
- **用户行为埋点**：双写 PostgreSQL + Redis 滑动窗口

## 文档索引

- [架构总览](docs/architecture/01-overview.md)
- [Agent 系统架构](docs/architecture/02-agent-system.md)
- [搜索与推荐系统](docs/architecture/03-search-system.md)
- [API 总览](docs/api/overview.md)
- [开发模块清单](docs/DEVELOPMENT_SUMMARY.md)

## 开发规范

- **提交格式**：`feat: / fix: / refactor: / chore: / test: / docs:` 前缀
- **分支策略**：GitHub Flow（main + dev 分支）
- **代码检查**：Python 用 `ruff` + `mypy`，TypeScript 用 `vue-tsc`
- **API 规范**：统一响应体 `{code, message, data}`
- **行长度**：120 字符 (Python)
- **类型注解**：`| None` 语法，`list[dict]` 泛型
