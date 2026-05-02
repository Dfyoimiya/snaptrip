# OpenCode 协作指令

本文件为 AI 编程助手（OpenCode/Claude/Copilot）提供项目协作规范。所有代码生成须遵守以下规则。

## 项目语境

SnapTrip 是面向美团 AI Hackathon 的全栈项目，目标是让用户通过自然语言输入，获得可执行的本地活动计划方案。

详见 [PROJECT.md](PROJECT.md) 获取完整语境。

## 协作原则

1. **先 Schema 后实现**：所有函数必须先有 Pydantic / TypeScript 类型定义
2. **禁止硬编码**：配置走 `config.py`，Prompt 走模板文件，数据走 seed 文件
3. **异步优先**：数据库、HTTP 调用全部使用 `async/await`
4. **错误处理**：所有外部调用必须 `try/except`，包装为业务异常
5. **结构化日志**：关键节点必须 `logger.info("event", key=value)` 格式

## 开发阶段优先级

按以下顺序执行。禁止跨阶段跳跃：

### 阶段 1：基础设施
- 创建 `docker-compose.yml` + `docker-compose.override.yml` + `.env.example`
- 创建 `backend/pyproject.toml`（uv + FastAPI 依赖）
- 创建 `frontend/package.json`（React + Vite + Tailwind）
- 创建 `mock_server/pyproject.toml`
- 创建 `Makefile`（含 `make dev` / `make init` / `make test-backend`）

### 阶段 2：后端骨架
- 创建 `backend/app/core/config.py`（Pydantic-Settings）
- 创建 `backend/app/core/logging.py`（structlog JSON）
- 创建 `backend/app/main.py`（App Factory + lifespan + 路由注册）
- 创建 `backend/app/db/session.py`（asyncpg + AsyncSessionLocal）
- 创建 `backend/app/models/base.py`（SQLAlchemy Base + TimestampMixin）
- 初始化 Alembic 并生成首版迁移

### 阶段 3：Mock 服务
- 创建 `mock_server/app/main.py`
- 创建 4 个 Router：poi、queue、booking、order
- 创建 `mock_server/app/data/seed_pois.json`（50 条 POI）

### 阶段 4：Agent 层
- 创建 Agent Hub 状态机
- 创建 Intent / Planning / Execution Agent
- 创建 Prompt 模板 + Skill 文件

### 阶段 5：前端骨架
- 创建三栏布局（地图 / Agent 大脑 / 计划卡片）
- 实现 SSE Hook + Plan API 调用

### 阶段 6：集成与测试
- 确保 `make dev` 一键启动全栈
- 编写单元测试 + 集成测试

## 代码规范

### Python
```python
# 行宽 100，ruff 格式化，mypy --strict
# 所有数据库操作必须 async
# 所有配置从 config.py 获取，禁止 os.getenv 散落

from app.core.config import settings
db_url = settings.DATABASE_URL  # ✅

db_url = os.getenv("DATABASE_URL")  # ❌
```

### TypeScript
```typescript
// strict: true，显式类型，禁止 any
const plans: PlanResponse[] = await getPlans(); // ✅
const data: any = await getPlans();              // ❌
```

### API 响应格式
```json
{
  "code": 0,
  "message": "success",
  "data": { ... }
}
```

### 提交格式
```
feat: 新增意图解析 Agent
fix: 修复规划算法硬约束过滤逻辑
refactor: 重构 Tool 编排器为 DAG 模式
test: 添加端到端规划链路集成测试
docs: 完善异常处理设计文档
```

## 关键约束

- Agent 框架通信走 ACP/HTTP 协议，不直接调用 Python 函数
- Prompt 必须放在 `backend/app/agents/prompts/` 下，Jinja2 模板
- Skill 文件格式：`## 触发条件` / `## 执行步骤` / `## 示例`
- 数据库表名复数（`plans`）、字段蛇形（`created_at`）
- 向量字段名统一使用 `embedding`，类型 `vector(1536)`
