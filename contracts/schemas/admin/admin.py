"""Admin domain DTOs — employee, role, statistics."""

from __future__ import annotations

from pydantic import BaseModel, Field

from pydantic import BaseModel as _BaseModel

from contracts.schemas.common import PaginationParams


# ── Auth ──

class AdminLoginReq(_BaseModel):
    username: str
    password: str


# ── Employee ──

class EmployeeResp(BaseModel):
    id: str
    username: str
    real_name: str
    phone: str
    avatar: str | None = None
    status: str  # "ACTIVE", "DISABLED"
    roles: list[str] = []  # role codes
    created_at: str


class EmployeeCreateReq(BaseModel):
    username: str = Field(min_length=3, max_length=20)
    password: str = Field(min_length=6, max_length=32)
    real_name: str = Field(min_length=1, max_length=20)
    phone: str = Field(pattern=r"^1[3-9]\d{9}$")
    role_codes: list[str] = []


class EmployeeUpdateReq(BaseModel):
    real_name: str | None = None
    phone: str | None = None
    status: str | None = None


class RoleAssignReq(BaseModel):
    role_codes: list[str]


# ── Role & Permission ──

class RoleResp(BaseModel):
    id: str
    role_code: str
    role_name: str
    description: str
    permission_codes: list[str] = []


class RoleCreateReq(BaseModel):
    role_code: str = Field(min_length=2, max_length=50)
    role_name: str = Field(min_length=1, max_length=20)
    description: str | None = None
    permission_codes: list[str] = []


class PermissionAssignReq(BaseModel):
    permission_codes: list[str]


class PermissionTreeResp(BaseModel):
    code: str
    name: str
    parent_code: str | None = None
    children: list["PermissionTreeResp"] = []


# ── Dashboard / Statistics ──

class DashboardStatsResp(BaseModel):
    today_revenue: int  # 分
    today_orders: int
    today_new_users: int
    pending_orders: int
    revenue_trend: list[dict]  # [{date, revenue}, ...]


class DateRangeQuery(BaseModel):
    start_date: str
    end_date: str


class RevenueStatsResp(BaseModel):
    total_revenue: int
    avg_daily_revenue: float
    daily_breakdown: list[dict]  # [{date, revenue, order_count}, ...]


class OrderStatsResp(BaseModel):
    total_orders: int
    completed_orders: int
    cancelled_orders: int
    completion_rate: float
    status_breakdown: dict[str, int]
    daily_breakdown: list[dict]


class UserStatsResp(BaseModel):
    total_users: int
    new_users: int
    active_users: int
    daily_breakdown: list[dict]


class ProductRankingResp(BaseModel):
    product_id: str
    product_name: str
    sales: int
    revenue: int
    rank: int
