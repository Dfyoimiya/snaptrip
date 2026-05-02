# 02 —— 10 天开发周期计划

## 总目标

在 10 个工作日内完成从零到可演示的全栈系统 `make dev` 一键启动。

## Phase × Module 映射

```
Phase 1: 基础设施 (Day 1)
  M1  Docker Compose 配置           [P_A]
  M2  backend/pyproject.toml       [P_A]
  M3  frontend/package.json        [P_C]
  M4  mock_server/pyproject.toml   [P_A]
  M5  Makefile                     [P_A]

Phase 2: 后端骨架 (Day 2-3)
  M6  core/config.py               [P_A]
  M7  core/logging.py              [P_A]
  M8  core/exceptions.py           [P_A]
  M9  core/constants.py            [P_A]
  M10 main.py                      [P_A]
  M11 db/session.py                [P_A]
  M12 models/base.py               [P_A]
  M13 models/user.py + plan.py + poi.py [P_A]
  M14 schemas/plan.py + user.py + common.py [P_A]
  M15 Alembic 初始迁移             [P_A]

Phase 3: Mock 服务 (Day 3-4)
  M16 mock_server/app/main.py      [P_C]
  M17 routers/poi.py               [P_C]
  M18 routers/queue.py             [P_C]
  M19 routers/booking.py           [P_C]
  M20 routers/order.py             [P_C]
  M21 seed_pois.json (50条)        [P_C]

Phase 4: Agent 层 (Day 4-6)
  M22 agents/protocol.py           [P_A] 先于实现
  M23 agents/hub.py                [P_B]
  M24 agents/intent_agent.py       [P_B]
  M25 agents/context_agent.py      [P_B]
  M26 agents/retrieval_agent.py    [P_B]
  M27 agents/planning_agent.py     [P_B]
  M28 agents/execution_agent.py    [P_B]
  M29 agents/fallback_agent.py     [P_B]
  M30 agents/notify_agent.py       [P_B]
  M31 prompts/*.j2 模板            [P_B]

Phase 5: 前端骨架 (Day 6-8)
  M32 frontend/src/main.tsx + App.tsx       [P_C]
  M33 components/MapView.tsx                [P_C]
  M34 components/AgentMonitor.tsx           [P_C]
  M35 components/PlanCard.tsx               [P_C]
  M36 hooks/useAgentStream.ts               [P_C]
  M37 api/plan.ts                           [P_C]
  M38 stores/planStore.ts                   [P_C]
  M39 types/plan.ts + sse.ts                [P_C]

Phase 6: 集成与测试 (Day 8-10)
  M40 make dev 全栈启动验证         [ALL]
  M41 unit/test_plan_service.py     [P_A]
  M42 unit/test_agents.py           [P_B]
  M43 integration/test_e2e.py       [P_A]
  M44 UI 打磨 + 动画                [P_C]
```

---

## 每日甘特图

```
         D1    D2    D3    D4    D5    D6    D7    D8    D9   D10
P_A  ████████████████████████████░░░░░░░░░░░░░░░░░░░░████████████
     M1-M5 M6-M15──────────────M22 ░░░░░░░░░░░░░░░░░░ M40-M44
P_B  ██░░░░░░░░░░░░░░░░████████████████████░░░░░░░░░░████████████
     阅读    ░░░░环境搭建  M23-M31─────────────░░░░░░░░ M40-M42
P_C  ██████████████████████████████████████████████░░░░████████████
     M3 阅读 M16-M21────── M32-M39──────────────────── M40-M44

图例: █ = 编码  ░ = 等待/缓冲
```

### Day 1 — Phase 1：基础设施（三人并行）

| 成员 | 任务 | 验收标准 |
|------|------|---------|
| P_A | M1 Docker + M2 pyproject + M4 mock pyproject + M5 Makefile | `docker compose up` 看到 postgres + redis 容器运行 |
| P_B | 阅读全部文档，搭建本地开发环境（uv + npm + docker） | 能运行 `make init` |
| P_C | M3 frontend/package.json + Vite 脚手架 | `npm run dev` 看到 Vite 默认页面 |

### Day 2 — Phase 2：后端骨架

| 成员 | 任务 | 验收标准 |
|------|------|---------|
| P_A | M6-M11 config/logging/main/db | `uvicorn main:app` 启动成功，`/docs` 可见 |
| P_B | 与 P_A 对齐 Agent 协议定义，起草 protocol.py | AgentContext / AgentResult 设计定稿 |
| P_C | 开始设计 Mock API OpenAPI spec + seed 数据调研 | POI 类型覆盖餐饮/景点/活动/咖啡馆 |

### Day 3 — Phase 2 收尾 + Phase 3 启动

| 成员 | 任务 | 验收标准 |
|------|------|---------|
| P_A | M12-M15 models + schemas + Alembic | `alembic upgrade head` 创建四张表成功 |
| P_B | 起草 hub.py 状态机设计 + intent.j2 prompt | 状态机流转图定稿 |
| P_C | M16-M17 mock main + poi router | `curl localhost:8001/mock/poi/search` 返回数据 |

**里程碑**：Phase 2 完成，Person A 产出完整 schemas/→ Person B 可以开始 Agent 开发

### Day 4 — Phase 3 + Phase 4 并行

| 成员 | 任务 | 验收标准 |
|------|------|---------|
| P_A | M22 agent/protocol.py (+ 补充 plan_service) | Agent 基类定义完成 |
| P_B | M24 intent_agent.py | 输入文本 → 输出 PlanConstraints |
| P_C | M18-M20 queue + booking + order routers | 全部 Mock API 端点可调用 |

### Day 5 — Agent 层核心

| 成员 | 任务 | 验收标准 |
|------|------|---------|
| P_B | M23 hub.py + M27 planning_agent.py | 状态机可串行调度 Intent → Planning |
| P_C | M21 seed_pois.json (50条) | 覆盖北京/上海/重庆三城 |
| P_A | 补充 API 路由 plan.py + user.py + deps.py | `POST /api/v1/plan/create` 返回 plan_id |

### Day 6 — Agent 层收尾 + 前端启动

| 成员 | 任务 | 验收标准 |
|------|------|---------|
| P_B | M25 M26 M28 M29 M30 全部 Agent | Agent 全链调通，Execution Agent 能调用 Mock API |
| P_C | M32 App.tsx + 三栏静态布局 + M39 类型定义 | 浏览器看到三栏骨架 |
| P_A | 对接 P_B 的 Agent 到路由层，实现 SSE 输出 | SSE endpoint 可推送事件 |

**里程碑**：Phase 4 完成，Agent 全链路可跑通

### Day 7 — 前端核心组件

| 成员 | 任务 | 验收标准 |
|------|------|---------|
| P_C | M33 MapView + M34 AgentMonitor + M36 useAgentStream | SSE 事件在浏览器终端风格面板中实时渲染 |
| P_B | Prompt 调优 + bug 修复 | 计划结果质量过关 |
| P_A | 补充 user API + 错误处理 | 异常情况有友好响应 |

### Day 8 — 前端收尾 + 联调开始

| 成员 | 任务 | 验收标准 |
|------|------|---------|
| P_C | M35 PlanCard + M37 API 封装 + M38 store | 完整三栏布局可交互 |
| P_A | 联调 SSH + 修复跨域/CORS/代理问题 | 前端能调通后端 |
| P_B | 联调 Agent + 异常演示（20% Mock 失败触发 Fallback） | Fallback 能正确定位和替换 |

### Day 9 — 集成冲刺

| 成员 | 任务 | 验收标准 |
|------|------|---------|
| ALL | M40 make dev 一键启动全栈 | 一条命令启动 DB+Redis+Backend+Frontend+Mock |
| P_A | M41 unit test + M43 e2e test | 关键路径测试通过 |
| P_C | M44 UI 打磨：动画 + 分享卡片 + 移动端适配 | 演示效果流畅 |

### Day 10 — 缓冲 + 演示准备

| 成员 | 任务 | 验收标准 |
|------|------|---------|
| ALL | Bug 修复、演示脚本排练、README 完善 | 可对外演示 |

---

## 验收标准（Definition of Done）

每个模块完成时必须满足：

- [ ] 代码通过 `ruff` 格式化 + `mypy --strict`（Python）/ `tsc --noEmit`（TypeScript）
- [ ] 新增文件有对应测试或已在 conftest.py 注册
- [ ] API 端点可通过 curl 验证
- [ ] 数据库变更通过 Alembic 迁移
- [ ] 新增依赖已写入 pyproject.toml / package.json
- [ ] 无 `os.getenv` 散落，全部走 config.py
- [ ] 无硬编码 Prompt，全部走 Jinja2 模板

## 风险与缓冲

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|---------|
| Hermes 集成复杂度超预期 | 中 | 高 | Day 4 前确认，必要时降级为自建轻量 Hub |
| pgvector 环境问题 | 低 | 中 | 使用 pgvector/pgvector Docker 镜像预装扩展 |
| 高德 API 配额/key 问题 | 低 | 中 | 前端 MapView 支持无 key 模式（Leaflet 降级） |
| Agent prompt 效果不达预期 | 中 | 中 | Day 7-8 集中调优，Day 10 前完成 |
| Mock 数据不够真实 | 低 | 低 | Day 5 前完成 seed 数据，Day 8 前可补充 |
