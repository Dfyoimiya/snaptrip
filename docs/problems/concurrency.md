# 并发与竞态问题清单

审查日期: 2026-06-20

## 严重

### GAP-1: 订单取消与支付存在 TOCTOU 竞态
- **文件**: `backend/app/services/order_service.py:476-519`
- **问题**: `cancel()` 先通过 `_validate_transition()` 检查当前状态为 PENDING_PAYMENT，再通过 ORM 赋值 `order.status = target_status` 更新。两次操作之间无原子性保证，如果支付回调并发地将状态改为 PAID，取消操作会覆盖支付结果。缺少 `UPDATE ... WHERE status = :old_status` 的原子条件更新。
- **影响**: 并发取消和支付可能导致已付款订单被错误取消，造成资金损失。

### GAP-2: 取消订单时 lock_stock 可能被并发扣成负数
- **文件**: `backend/app/services/order_service.py:502-507`
- **问题**: 库存释放使用 `update(PmsSku).where(PmsSku.id == item.sku_id).values(lock_stock=PmsSku.lock_stock - item.quantity)`，WHERE 条件只按 ID 匹配，不校验 `lock_stock >= item.quantity`。并发取消同一订单可能导致 lock_stock 被重复扣减至负数。
- **影响**: 库存数据错误，可能导致超卖或账务不一致。

### GAP-3: Agent 全局 `_runtime` 跨请求共享可变状态
- **文件**: `agent/src/agent/graph.py:44,105`
- **问题**: `_runtime: AgentRuntime | None = None` 是模块级全局变量，在 `build_graph()` 时设置。所有并发请求共享同一 `_runtime`，包括 `ToolHarness`、`SessionContext`、`event_bus`。不同请求可能相互覆盖 `session_ctx` 中的用户信息。
- **影响**: 用户 A 的请求可能使用用户 B 的会话上下文，导致数据泄露或越权操作。

### GAP-4: SessionContext 在并发请求间可变共享
- **文件**: `agent/src/agent/tools/harness/harness.py:108-114`
- **问题**: `runtime.session_ctx = SessionContext()` 设置为单例，`session_ctx.metadata["auth_token"]` 被多个请求共享修改。虽然 `auth_token` 使用 ContextVar 传递，但 metadata dict 本身无隔离。
- **影响**: 认证凭据可能在不同请求间串扰。

## 高

### GAP-5: auto_cancel_expired_orders / auto_confirm_receipt_orders 是死代码
- **文件**: `backend/app/tasks/order_tasks.py:20,97`，`backend/marketplace/app/celery_app.py:42-68`
- **问题**: 两个 `@shared_task` 定义了但从未注册到 `beat_schedule`。`auto_confirm_receipt_orders` 的 docstring 引用了不存在的 `crontab` 配置。`celery_app.py` 未导入 `celery.schedules.crontab`。
- **影响**: 过期订单永远不会自动取消，已签收订单永远不会自动确认收货。

### GAP-6: Saga reserve 阶段实际执行了取消操作
- **文件**: `agent/src/agent/tools/transaction/saga.py:96-100`，`agent/src/agent/tools/transaction/cancel_order.py:34-64`
- **问题**: `CancelOrderTool._arun()` 不检查 `reserve_only` 参数，无条件 POST 取消。Saga 的 reserve 阶段本应仅"预留"取消权，但实际执行了取消。confirm 阶段再次 POST 取消会失败（订单已取消）。
- **影响**: Saga 事务语义被破坏，取消操作无法回滚。

### GAP-7: 混合搜索 asyncio.gather() 无超时保护
- **文件**: `backend/app/services/hybrid_search_service.py:109-114`
- **问题**: ES、向量、CF 三个并发协程通过 `asyncio.gather()` 执行，无 `asyncio.wait_for()` 超时。任一搜索源挂起（如 ES 超时）将永久阻塞整个搜索请求。
- **影响**: 搜索接口可能无限期挂起，耗尽 FastAPI worker。

### GAP-8: Agent 节点 LLM 调用无超时
- **文件**: `agent/src/agent/nodes/recommendation/user_profile.py:97`，`agent/src/agent/nodes/recommendation/product_rec.py:236`
- **问题**: LLM 调用未包裹 `asyncio.wait_for()`。Agent 定义了 `timeout` 属性但未程序化执行。如果 LLM API 挂起，LangGraph 执行永久阻塞。
- **影响**: Agent 请求可能永远不会返回，资源泄漏。

## 中

### GAP-9: SLA 监控和优惠券过期任务无分布式锁
- **文件**: `backend/marketplace/app/celery_app.py:49-65`
- **问题**: `cs_sla_monitor` 和 `auto_expire_coupons` 每 60s 触发，`task_acks_late=True` 允许确认延迟。如果上一次执行未完成，新调用会并发启动。无 Redis 锁防止重叠执行。
- **影响**: 同一业务逻辑可能并发执行两次，虽然当前有 WHERE 条件保护，但浪费资源。

### GAP-10: get_trending_queries() 速度检测逻辑有 bug
- **文件**: `backend/app/services/trending_service.py:165-183`
- **问题**: 循环 `range(1, 13)` 调用 `zset_zcard()` 但结果未存入 `baseline_counts`，导致 `baseline_counts.get(query, 1.0)` 始终返回默认值 1.0。速度检测退化为原始计数。
- **影响**: 趋势检测功能实际不工作，所有查询的速度指标完全相同。

### GAP-11: ES async_bulk 部分失败被静默丢弃
- **文件**: `backend/app/search/client.py:115-116`
- **问题**: `async_bulk` 返回 `(success, errors)`，代码只用 `success` 计数，`errors` 被忽略。部分文档索引失败时无日志、无重试。
- **影响**: ES 索引不完整，部分商品搜索不到。

### GAP-12: Celery 任务每调用连接断开后重建
- **文件**: `backend/app/tasks/order_tasks.py:46-48`（及其他任务文件）
- **问题**: 每个 Celery 任务开头调用 `await async_engine.dispose()` 销毁连接池，配合 NullPool 导致每次执行都重新建立数据库连接。
- **影响**: 性能开销，高频率任务（60s 间隔）产生连接抖动。

## 低

### GAP-13: Dashboard 8 个独立 DB 查询串行执行
- **文件**: `backend/app/api/admin/dashboard.py:43-50`
- **问题**: `get_dashboard()` 串行执行 `count_today()`、`revenue_today()` 等 8 个独立查询。可用 `asyncio.gather()` 并行化减少延迟。
- **影响**: Dashboard 加载延迟约 8 × 单次查询时间。

### GAP-14: 推荐子图 asyncio.gather() 无超时
- **文件**: `agent/src/agent/nodes/recommendation/graph.py:86-92,122-134`
- **问题**: `_parallel_phase1` 和 `_parallel_phase2` 中两个 Agent 并发执行无整体超时控制。任一 Agent 挂起则整个推荐管线挂起。
- **影响**: 推荐请求可能无限期挂起。

### GAP-15: SentenceTransformer 单例非线程安全
- **文件**: `backend/app/services/hybrid_search_service.py:657-668`
- **问题**: `_local_embedding_model` 是模块级单例，通过 `asyncio.to_thread()` 调度到线程池并发调用 `encode()`。SentenceTransformer 不保证 `encode()` 线程安全。
- **影响**: 高并发下可能产生未定义行为或随机错误。

### GAP-16: ES 单例懒初始化无重入保护
- **文件**: `backend/app/search/client.py:297-305`
- **问题**: `get_search_client()` 使用简单的 `if _search_client is None` 检查创建单例。多 worker 或 Celery 任务并发启动时可能创建多个实例。
- **影响**: 多个 ES 客户端实例，连接资源浪费。

## 统计

| 严重 | 高 | 中 | 低 |
|------|-----|-----|-----|
| 4 | 4 | 4 | 4 |
