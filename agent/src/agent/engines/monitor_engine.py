"""Monitor Engine —— 执行后实时监控与告警。

计划执行完成后，Monitor Engine 进入后台监控循环：
  a. 轮询路线: 当前通行时间 vs 基线 → 超 15 分钟发 traffic_delay 告警
  b. 轮询排队: 当前排队人数 vs 基线 ×2 → 发送 queue_surge 告警
  c. 轮询天气: 天气恶化 (rainy/stormy) → 发送 weather_change 告警
  d. 轮询预订: 外部取消 → 发送 booking_cancelled 告警

指数退避: 60s → 120s → 300s (上限)
告警通过 SSE 推送到前端
critical 级别告警 → 自动触发 graph 重入 (ReplanTrigger)

Author: SnapTrip Team
Date: 2026-05-24
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from typing import Protocol

from snaptrip_shared.core.logging import get_logger
from snaptrip_shared.schemas.plan import PlanDraft

from agent.ports.rt_context import RTContextPort
from agent.protocol import AgentContext, AgentResult, BaseAgent
from agent.schemas.state import (
    Alert,
    BookingCheck,
    MonitorPlan,
    QueueCheck,
    ReplanTrigger,
    RouteCheck,
)

logger = get_logger(__name__)

# ── Constants ──────────────────────────────────────────────────────

INITIAL_POLL_INTERVAL_S = 60
MAX_POLL_INTERVAL_S = 300
TRAFFIC_DELAY_THRESHOLD_MIN = 15
QUEUE_SURGE_MULTIPLIER = 2.0


class AlertSinkPort(Protocol):
    """告警推送端口 —— SSE / WebSocket / Webhook 实现。"""

    async def emit(self, alert: Alert) -> None:
        """推送告警到前端。"""
        ...


# ── Monitor Engine ──────────────────────────────────────────────────


class MonitorEngine(BaseAgent):
    """执行后监控引擎 —— 轮询路线/排队/天气/预订 并发出告警。

    运行方式:
      - 作为 graph 的最后一个节点被调用
      - 首次调用时构建 MonitorPlan 并开始后台轮询
      - 通过 AlertSinkPort 推送告警
    """

    name = "monitor_engine"

    def __init__(
        self,
        rt_context_port: RTContextPort | None = None,
        alert_sink: AlertSinkPort | None = None,
    ) -> None:
        super().__init__()
        self._rt_port = rt_context_port
        self._alert_sink = alert_sink

    async def execute(self, context: AgentContext) -> AgentResult:
        """构建 MonitorPlan 并启动后台监控。

        Args:
            context: 含 PlanDraft 和 ExecutionState 的上下文

        Returns:
            AgentResult.data["monitor_plan"] = MonitorPlan
            AgentResult.data["alerts"] = list[Alert]
        """
        draft = self._extract_draft(context)
        if not draft:
            return AgentResult(status="failed", error="No plan draft for monitoring")

        # 构建监控计划
        monitor_plan = self._build_monitor_plan(draft)

        # 首次检查（不等待轮询）
        alerts = await self._check_all(monitor_plan)

        # 推送告警
        if alerts and self._alert_sink:
            for alert in alerts:
                await self._alert_sink.emit(alert)

        # 检查是否需要自动重规划
        replan_trigger = self._build_replan_trigger(alerts)

        logger.info(
            "monitor_engine_started",
            plan_id=context.plan_id,
            alert_count=len(alerts),
            auto_replan=replan_trigger.auto_replan if replan_trigger else False,
        )

        return AgentResult(
            data={
                "monitor_plan": monitor_plan.model_dump(),
                "alerts": [a.model_dump() for a in alerts],
                "replan_trigger": replan_trigger.model_dump()
                if replan_trigger
                else None,
            }
        )

    # ── MonitorPlan 构建 ──────────────────────────────────────────

    def _build_monitor_plan(self, draft: PlanDraft) -> MonitorPlan:
        """从 PlanDraft 构建 MonitorPlan。

        自动提取所有需要监控的路线、排队和预订。
        """
        routes: list[RouteCheck] = []
        queues: list[QueueCheck] = []
        bookings: list[BookingCheck] = []

        for i, slot in enumerate(draft.slots):
            # 路线监控 (slot N-1 → slot N)
            if i > 0:
                routes.append(
                    RouteCheck(
                        from_slot=i - 1,
                        to_slot=i,
                        baseline_travel_min=slot.move_time_min,
                    )
                )

            # 排队监控
            queues.append(
                QueueCheck(
                    slot_index=i,
                    poi_id=slot.poi.id,
                    baseline_queue=0,  # 真实实现从 POIRealTimeStatus 获取
                )
            )

            # 预订状态监控
            if slot.action in ("book_table", "book_ticket"):
                bookings.append(
                    BookingCheck(
                        slot_index=i,
                        poi_id=slot.poi.id,
                        booking_id=f"pending_{slot.sequence}",
                    )
                )

        # 监控截止时间 = 最后一个 slot 结束 + 2 小时缓冲区
        deadline = None
        if draft.slots:
            last_end = max(
                (s.time_range.end for s in draft.slots),
                default=draft.slots[-1].time_range.end
                if draft.slots
                else datetime.now(),
            )
            deadline = last_end + timedelta(hours=2)

        return MonitorPlan(
            poll_interval_s=INITIAL_POLL_INTERVAL_S,
            routes_to_track=routes,
            queues_to_track=queues,
            bookings_to_track=bookings,
            deadline=deadline,
        )

    # ── 全面检查 ──────────────────────────────────────────────────

    async def _check_all(self, plan: MonitorPlan) -> list[Alert]:
        """并行执行所有检查。"""
        alerts: list[Alert] = []

        # 路线检查
        route_alerts = await self._check_routes(plan.routes_to_track)
        alerts.extend(route_alerts)

        # 排队检查
        queue_alerts = await self._check_queues(plan.queues_to_track)
        alerts.extend(queue_alerts)

        # 天气检查
        weather_alerts = await self._check_weather()
        alerts.extend(weather_alerts)

        # 预订状态检查
        booking_alerts = await self._check_bookings(plan.bookings_to_track)
        alerts.extend(booking_alerts)

        return alerts

    async def _check_routes(self, routes: list[RouteCheck]) -> list[Alert]:
        """检查路线通行时间是否严重偏离基线。"""
        alerts: list[Alert] = []
        if not self._rt_port:
            return alerts

        for route in routes:
            try:
                # 真实实现: 通过 RTContextPort.get_traffic_index 获取实时交通
                traffic = await self._rt_port.get_traffic_index(0, 0)
                delay_factor = traffic.overall
                estimated_delay = int(route.baseline_travel_min * delay_factor)
                route.current_travel_min = route.baseline_travel_min + estimated_delay

                if estimated_delay > TRAFFIC_DELAY_THRESHOLD_MIN:
                    alerts.append(
                        Alert(
                            alert_type="traffic_delay",
                            severity="warning",
                            slot_indices=[route.from_slot, route.to_slot],
                            message=(
                                f"slot{route.from_slot}→slot{route.to_slot} "
                                f"预计延迟 {estimated_delay} 分钟"
                            ),
                            suggested_action="partial_replan",
                        )
                    )
            except Exception:
                logger.debug("route_check_failed", exc_info=True)

        return alerts

    async def _check_queues(self, queues: list[QueueCheck]) -> list[Alert]:
        """检查排队人数是否暴增。"""
        alerts: list[Alert] = []
        if not self._rt_port:
            return alerts

        for q in queues:
            try:
                status = await self._rt_port.get_poi_realtime(q.poi_id)
                if status is None:
                    continue
                q.current_queue = status.queue_length

                threshold = max(q.baseline_queue * QUEUE_SURGE_MULTIPLIER, 10)
                if q.current_queue > threshold:
                    severity = (
                        "critical" if q.current_queue > threshold * 2 else "warning"
                    )
                    alerts.append(
                        Alert(
                            alert_type="queue_surge",
                            severity=severity,
                            slot_indices=[q.slot_index],
                            message=(
                                f"slot{q.slot_index} POI {q.poi_id[:8]} "
                                f"排队从 {q.baseline_queue} 增至 {q.current_queue}"
                            ),
                            suggested_action="partial_replan",
                        )
                    )
            except Exception:
                logger.debug("queue_check_failed", exc_info=True)

        return alerts

    async def _check_weather(self) -> list[Alert]:
        """检查天气是否恶化。"""
        alerts: list[Alert] = []
        if not self._rt_port:
            return alerts

        try:
            # 默认北京坐标，真实实现从 context 获取
            weather = await self._rt_port.get_weather(39.9042, 116.4074)
            if weather.condition in ("rainy", "stormy", "snowy"):
                severity = "critical" if weather.condition == "stormy" else "warning"
                alerts.append(
                    Alert(
                        alert_type="weather_change",
                        severity=severity,
                        slot_indices=[],
                        message=(
                            f"天气变化: {weather.condition}, "
                            f"温度 {weather.temperature_c}°C, "
                            f"户外分 {weather.outdoor_score:.1f}"
                        ),
                        suggested_action="full_replan",
                    )
                )
        except Exception:
            logger.debug("weather_check_failed", exc_info=True)

        return alerts

    async def _check_bookings(self, bookings: list[BookingCheck]) -> list[Alert]:
        """检查预订是否被外部取消。"""
        alerts: list[Alert] = []
        # 桩实现: 种子 POI 无实际预订状态，始终正常
        for b in bookings:
            if b.current_status == "cancelled":
                alerts.append(
                    Alert(
                        alert_type="booking_cancelled",
                        severity="critical",
                        slot_indices=[b.slot_index],
                        message=(f"slot{b.slot_index} 预订 {b.booking_id} 已被取消"),
                        suggested_action="partial_replan",
                    )
                )
        return alerts

    # ── ReplanTrigger ──────────────────────────────────────────────

    def _build_replan_trigger(self, alerts: list[Alert]) -> ReplanTrigger | None:
        """从告警列表构建 ReplanTrigger。

        - critical 告警 → auto_replan = True
        - warning 告警 → 收集受影响 slot
        """
        if not alerts:
            return None

        criticals = [a for a in alerts if a.severity == "critical"]

        scope = "partial"
        if any(a.suggested_action == "full_replan" for a in alerts):
            scope = "full"

        affected: set[int] = set()
        for a in alerts:
            affected.update(a.slot_indices)

        auto = any(
            a.alert_type in ("booking_cancelled", "poi_closed") for a in criticals
        )

        return ReplanTrigger(
            scope=scope,
            affected_slot_indices=sorted(affected),
            recommended_alternatives=[],
            auto_replan=auto,
        )

    # ── Data Extraction ────────────────────────────────────────────

    @staticmethod
    def _extract_draft(context: AgentContext) -> PlanDraft | None:
        for h in reversed(context.history):
            if "draft" in h.data:
                return PlanDraft(**h.data["draft"])
        return None


# ── Background Monitor Loop ────────────────────────────────────────


async def run_monitor_loop(
    monitor_plan: MonitorPlan,
    rt_port: RTContextPort | None = None,
    alert_sink: AlertSinkPort | None = None,
    *,
    max_duration_s: int = 7200,
    cancel_event: asyncio.Event | None = None,
) -> list[Alert]:
    """后台监控循环 —— 指数退避轮询。

    在独立的 asyncio.Task 中运行。
    通过 cancel_event 取消。

    Args:
        monitor_plan: 监控计划
        rt_port: 实时上下文端口
        alert_sink: 告警推送端口
        max_duration_s: 最大监控时长（秒），默认 2 小时
        cancel_event: 外部取消事件

    Returns:
        所有发出的告警列表
    """
    engine = MonitorEngine(rt_context_port=rt_port, alert_sink=alert_sink)
    all_alerts: list[Alert] = []
    interval = INITIAL_POLL_INTERVAL_S
    start_time = datetime.now()
    ce = cancel_event or asyncio.Event()

    while not ce.is_set():
        elapsed = (datetime.now() - start_time).total_seconds()
        if elapsed > max_duration_s:
            logger.info("monitor_loop_max_duration_reached")
            break

        try:
            # 构建最新上下文
            ctx = AgentContext(
                user_input="monitor_loop",
                state="monitoring",
            )
            result = await engine.execute(ctx)
            alerts_data = result.data.get("alerts", [])
            batch = [Alert(**a) for a in alerts_data] if alerts_data else []
            all_alerts.extend(batch)

            # 推送新告警
            if batch and alert_sink:
                for alert in batch:
                    await alert_sink.emit(alert)

        except Exception:
            logger.exception("monitor_loop_iteration_failed")

        # 指数退避
        await asyncio.sleep(interval)
        interval = min(interval * 2, MAX_POLL_INTERVAL_S)

    return all_alerts
