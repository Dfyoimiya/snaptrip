# SnapTrip —— 本地生活智能规划与执行系统

> 美团 AI Hackathon 命题 1.6：本地场景短时活动规划与执行 Agent

**一句话描述**：自然语言输入 →  Agent 规划执行 → 可执行时间轴方案 → Mock 预订 → 订单展现

## 产品闭环

```
用户输入"今天下午有空，想和朋友出去玩"
  → 意图解析（Intent）
  → POI 检索（Retrieval）
  → 时空规划（Planning）
  → 自动预订（Execution）
  → 异常自愈（Fallback）
  → 分享通知（Notify）
```

## 技术栈

| 层级 | 技术 |
|------|------|
| Agent 框架 | LangGraph (StateGraph + PostgresSaver) |
| LLM 网关 | OpenRouter (DeepSeek-V3 / Claude-3.5-Sonnet) |
| 后端 | FastAPI + Pydantic v2 + SQLAlchemy 2.0 |
| 数据库 | PostgreSQL 16 + pgvector |
| 缓存/队列 | Redis + Celery |
| 前端 | React 18 + TypeScript + Tailwind + Vite |
| Mock 服务 | FastAPI 子服务（模拟美团 API） |
| 部署 | Docker Compose |

## 快速开始

### 前置要求

- Docker Desktop 4.x+
- Python 3.11+
- Node.js 20+
- uv (Python 包管理器)

### 一键启动

```bash
# 1. 克隆项目
git clone <repo-url> && cd snaptrip

# 2. 初始化（复制 .env、安装依赖）
make init

# 3. 启动全栈（DB + Redis + Backend + Frontend + Mock）
make up
```

### 服务端口

| 服务 | 端口 | 访问地址 |
|------|------|----------|
| 后端 API | 8080 | http://localhost:8080/docs |
| Mock 服务 | 8001 | http://localhost:8001/docs |
| 前端 | 5174 | http://localhost:5174 |
| PostgreSQL | 5432 | — |
| Redis | 6379 | — |

### 开发命令

```bash
make dev            # 启动开发环境（热重载）
make test-backend   # 运行后端测试
make lint           # 代码检查（ruff + mypy）
make migrate        # 生成数据库迁移
```

## 项目结构

```
snaptrip/
├── backend/              # FastAPI API 网关
│   ├── marketplace/      # 业务代码 (api/models/services)
│   ├── alembic/          # 数据库迁移
│   └── tests/            # 单元 + 集成测试
├── agent/                # LangGraph Agent 引擎
│   └── src/agent/        # engines/adapters/tasks
├── shared/               # 共享库 (config/db/schemas)
│   └── snaptrip_shared/
├── mock-services/        # Mock 外部 API
│   └── mock-meituan/     # 模拟美团 API
├── frontend/             # React 19 前端
├── docs/                 # 架构文档
├── docker-compose.yml
└── Makefile
```

## 核心特性

- **两阶段规划算法**：硬约束过滤（非 LLM）+ 软约束排序（LLM）
- **Tool DAG + Saga**：依赖图编排 + 补偿事务
- **SSE 流式输出**：Agent 思考过程实时推送到前端
- **异常自愈**：预订失败时自动 Fallback 重规划
- **向量记忆**：pgvector 持久化用户偏好跨会话复用

## 文档索引

- [架构总览](docs/architecture/01-overview.md)
- [规划算法](docs/architecture/02-planning-algorithm.md)
- [Tool 编排](docs/architecture/03-tool-orchestration.md)
- [异常处理](docs/architecture/04-exception-handling.md)
- [Plan API](docs/api/plan.md)

## 开发规范

- **提交格式**：`feat: / fix: / refactor: / test: / docs:` 前缀
- **分支策略**：GitHub Flow（main + feature 分支）
- **代码检查**：Python 用 `ruff` + `mypy --strict`，TS 用 `strict: true`
- **API 规范**：统一响应体 `{code, message, data}`
