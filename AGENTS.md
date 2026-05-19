# OpenCode 协作指令

本文件为 AI 编程助手（OpenCode/Claude/Copilot）提供项目协作规范。所有代码生成须遵守以下规则。

## 项目语境

SnapTrip 是面向美团生活服务的全栈agent项目，目标是让用户通过自然语言输入，获得可执行的本地活动计划方案，并实际完成工具调用执行。

详见 [PROJECT.md](PROJECT.md) 获取完整语境。

## 协作原则

1. **先 Schema 后实现**：所有函数必须先有 Pydantic / TypeScript 类型定义
2. **禁止硬编码**：配置走 `config.py`，Prompt 走模板文件，数据走 seed 文件
3. **异步优先**：数据库、HTTP 调用全部使用 `async/await`
4. **错误处理**：所有外部调用必须 `try/except`，包装为业务异常
5. **结构化日志**：关键节点必须 `logger.info("event", key=value)` 格式

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

- **Agent 通信协议（已更新）**：
  - 竞赛核心 9 Agent 运行在同一个 FastAPI 事件循环中，通过 `AgentContext` + `AgentResult` Schema 做同进程内存传递（零序列化开销，适合 hackathon 规模）。
  - 仅 Execution Engine 调用 Mock API 时走 HTTP（`MockAPIGateway`）。
  - 未来若需横向扩展（新增 Recommend / Review / Dispatch 等课设 Agent），应引入 **AgentBus (Redis Pub/Sub)** 或 **ACP/HTTP** 消息协议，当前已预留 `ConsensusResolver` 等多利益方协商接口。
- Prompt 必须放在 `backend/app/agents/prompts/` 下，Jinja2 模板
- Skill 文件格式：`## 触发条件` / `## 执行步骤` / `## 示例`，代码级 Skill 放在 `backend/app/agents/skills/`
- 数据库表名复数（`plans`）、字段蛇形（`created_at`）
- 向量字段名统一使用 `embedding`，类型 `vector(1536)`
