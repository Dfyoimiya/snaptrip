"""Mock Server 统一响应模型 —— 模拟美团本地生活 API。

参考美团开放平台 API 设计:
  - 团购/到店消费: https://open.meituan.com/
  - 外卖: https://developer.waimai.meituan.com/
  - 电影/演出: 猫眼电影 API
  - 酒店: 美团酒店 API

Author: SnapTrip Team
Date: 2026-05-30
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# =============================================================================
# 通用响应模型
# =============================================================================


class ToolResult(BaseModel):
    """通用 API 响应（保持向后兼容）。"""
    status: str = "success"
    data: dict[str, Any] | None = None
    error_code: str | None = None
    error_message: str | None = None
    latency_ms: int = 0


class PaginatedData(BaseModel):
    """分页数据。"""
    items: list[Any] = []
    total: int = 0
    page: int = 1
    page_size: int = 20
    has_more: bool = False


# =============================================================================
# 通用枚举
# =============================================================================


class POICategory(str, Enum):
    """POI 品类（参考美团品类体系）。"""
    RESTAURANT = "restaurant"         # 餐厅
    CAFE = "cafe"                     # 咖啡/茶饮
    BAKERY = "bakery"                 # 烘焙/甜品
    FAST_FOOD = "fast_food"           # 快餐/小吃
    BAR = "bar"                       # 酒吧
    ATTRACTION = "attraction"         # 景点/地标
    EXHIBITION = "exhibition"         # 展览/博物馆
    PLAYGROUND = "playground"         # 游乐园/亲子
    ACTIVITY = "activity"             # 户外活动
    FLOWER = "flower"                 # 花店
    CINEMA = "cinema"                 # 电影院
    KTV = "ktv"                       # KTV
    ESCAPE_ROOM = "escape_room"       # 密室/剧本杀
    BOARD_GAME = "board_game"         # 桌游
    SPORT_VENUE = "sport_venue"       # 运动场馆
    SPA = "spa"                       # 按摩/SPA
    HOTEL = "hotel"                   # 酒店
    SCENIC = "scenic"                 # 景区
    SHOPPING = "shopping"             # 购物


class GroupType(str, Enum):
    """出行人群类型。"""
    FAMILY = "family"     # 亲子家庭
    FRIENDS = "friends"   # 朋友聚会
    COUPLE = "couple"     # 情侣约会
    SOLO = "solo"         # 独自出行


class OrderStatus(str, Enum):
    """订单状态（参考美团订单状态机）。"""
    PREPARED = "prepared"         # 待提交
    PENDING = "pending"           # 待支付
    PAID = "paid"                 # 已支付
    CONFIRMED = "confirmed"       # 已确认
    PREPARING = "preparing"       # 准备中（外卖）
    DELIVERING = "delivering"     # 配送中
    COMPLETED = "completed"       # 已完成
    CANCELLED = "cancelled"       # 已取消
    REFUNDING = "refunding"       # 退款中
    REFUNDED = "refunded"         # 已退款


class PayMethod(str, Enum):
    """支付方式。"""
    WECHAT = "wechat"
    ALIPAY = "alipay"
    MEITUAN_PAY = "meituan_pay"
    UNION_PAY = "union_pay"


class DeliveryMode(str, Enum):
    """出行方式。"""
    WALK = "walk"
    DRIVE = "drive"
    TRANSIT = "transit"
    CYCLING = "cycling"


# =============================================================================
# POI / 门店
# =============================================================================


class POIItem(BaseModel):
    """POI 数据项。"""
    id: str
    name: str
    city: str
    lat: float
    lng: float
    category: POICategory
    tags: list[str] = []
    avg_rating: float = 0.0
    price_level: int = 0         # 0=免费 1=人均<50 2=50-150 3=150-300 4=>300
    open_hours: str = ""          # "10:00-22:00"
    phone: str = ""
    address: str = ""
    thumbnail: str = ""           # 缩略图 URL
    photos: list[str] = []
    distance_km: float = 0.0
    group_suitability: dict[str, float] = {}  # group_type -> score


# =============================================================================
# 餐厅预订
# =============================================================================


class ReservationRequest(BaseModel):
    """餐厅订座请求。"""
    poi_id: str
    user_id: str
    date: str                     # "2026-05-31"
    time_slot: str                # "18:30"
    party_size: int = Field(default=2, ge=1, le=20)
    table_type: str = "hall"      # hall / private_room / outdoor
    special_requirements: str = ""  # 特殊需求（靠窗/无烟区等）
    contact_name: str = ""
    contact_phone: str = ""


class ReservationResult(BaseModel):
    """餐厅订座结果。"""
    reservation_id: str
    poi_id: str
    status: str                   # confirmed / waitlisted / rejected
    table_no: str = ""
    confirm_deadline: str = ""    # 确认截止时间


# =============================================================================
# 外卖
# =============================================================================


class TakeoutMerchant(BaseModel):
    """外卖商家。"""
    id: str
    name: str
    city: str
    lat: float
    lng: float
    category: str                 # 中式快餐/西式快餐/日料等
    avg_rating: float
    monthly_sales: int            # 月销量
    delivery_fee: float           # 配送费
    min_order: float              # 起送价
    delivery_time_min: int        # 预计送达时间下限（分钟）
    delivery_time_max: int        # 预计送达时间上限
    distance_km: float
    tags: list[str] = []
    thumbnail: str = ""


class MenuItem(BaseModel):
    """菜品/商品。"""
    id: str
    name: str
    category: str                 # 招牌/主食/饮品/小食等
    price: float
    original_price: float = 0.0   # 原价（划线价）
    monthly_sales: int = 0        # 月销量
    rating: float = 0.0
    image: str = ""
    description: str = ""


class TakeoutOrderRequest(BaseModel):
    """外卖下单请求。"""
    poi_id: str
    user_id: str
    items: list[dict]             # [{menu_id, quantity, specs: [...]}]
    remark: str = ""              # 备注
    address_id: str = ""
    coupon_id: str = ""
    delivery_time_type: str = "asap"  # asap / scheduled
    scheduled_time: str = ""


# =============================================================================
# 团购/优惠券
# =============================================================================


class CouponItem(BaseModel):
    """团购券/套餐。"""
    id: str
    poi_id: str
    title: str
    description: str = ""
    original_price: float
    sale_price: float
    sold_count: int = 0           # 已售
    valid_from: str = ""
    valid_to: str = ""
    use_rules: list[str] = []     # 使用规则
    is_refundable: bool = True
    refund_condition: str = ""    # "随时退" / "过期退"


# =============================================================================
# 电影
# =============================================================================


class MovieItem(BaseModel):
    """影片信息。"""
    id: str
    title: str
    title_en: str = ""
    category: str                 # 动作/喜剧/动画等
    duration_min: int             # 片长（分钟）
    director: str = ""
    cast: list[str] = []
    rating: float = 0.0
    want_count: int = 0           # 想看人数
    gross: str = ""               # 票房
    poster: str = ""
    trailer: str = ""
    synopsis: str = ""
    release_date: str = ""
    is_now_showing: bool = True


class CinemaItem(BaseModel):
    """影院信息。"""
    id: str
    name: str
    city: str
    lat: float
    lng: float
    address: str = ""
    distance_km: float = 0.0
    hall_count: int = 0
    tags: list[str] = []          # IMAX /杜比/4K等
    avg_rating: float = 0.0


class MovieSession(BaseModel):
    """电影场次。"""
    session_id: str
    movie_id: str
    cinema_id: str
    hall_name: str                # "1号激光IMAX厅"
    hall_type: str = ""           # IMAX /杜比/普通
    date: str                     # "2026-05-31"
    start_time: str               # "19:30"
    end_time: str                 # "21:30"
    language: str = "国语"
    dimension: str = "2D"         # 2D / 3D / IMAX 3D
    base_price: float             # 原价
    vip_price: float = 0.0


class SeatInfo(BaseModel):
    """座位信息。"""
    row: int
    col: int
    seat_name: str = ""           # "5排12座"
    status: str                   # available/sold/locked
    price: float = 0.0
    is_couple_seat: bool = False


class MovieOrderRequest(BaseModel):
    """选座购票请求。"""
    session_id: str
    user_id: str
    seats: list[str]              # ["5-12", "5-13"]
    mobile: str = ""


# =============================================================================
# 演出/赛事
# =============================================================================


class ShowItem(BaseModel):
    """演出/赛事信息。"""
    id: str
    title: str
    category: str                 # concert/drama/sport/exhibition/etc
    venue_name: str
    city: str
    lat: float
    lng: float
    poster: str = ""
    artists: list[str] = []
    date_range: list[str] = []    # ["2026-06-01", "2026-06-03"]
    min_price: float
    max_price: float
    status: str = "on_sale"       # on_sale/sold_out/ended
    tags: list[str] = []


# =============================================================================
# 休闲娱乐
# =============================================================================


class LeisureVenue(BaseModel):
    """休闲娱乐场所。"""
    id: str
    name: str
    city: str
    lat: float
    lng: float
    category: str                 # KTV/密室/剧本杀/桌游/酒吧等
    avg_rating: float
    price_level: int
    distance_km: float = 0.0
    open_hours: str = ""
    tags: list[str] = []
    thumbnail: str = ""


class TimeSlotAvailability(BaseModel):
    """可预订时段。"""
    date: str
    time_slot: str                # "14:00-16:00"
    room_type: str = ""           # 房型/包间类型
    price: float
    is_available: bool = True
    remaining_count: int = 1


# =============================================================================
# 运动场馆
# =============================================================================


class SportVenue(BaseModel):
    """运动场馆。"""
    id: str
    name: str
    city: str
    lat: float
    lng: float
    sport_type: str               # badminton/basketball/swimming/tennis等
    avg_rating: float
    distance_km: float = 0.0
    court_count: int = 0
    open_hours: str = ""
    tags: list[str] = []
    thumbnail: str = ""


class CourtSlot(BaseModel):
    """场地时段。"""
    date: str
    court_no: int
    start_time: str
    end_time: str
    price: float
    is_available: bool = True


# =============================================================================
# 酒店
# =============================================================================


class HotelItem(BaseModel):
    """酒店信息。"""
    id: str
    name: str
    city: str
    lat: float
    lng: float
    star_level: int = 3           # 星级 3-5
    avg_rating: float = 0.0
    distance_km: float = 0.0
    address: str = ""
    tags: list[str] = []
    facilities: list[str] = []    # WiFi/停车场/泳池等
    thumbnail: str = ""
    photos: list[str] = []


class RoomType(BaseModel):
    """房型信息。"""
    id: str
    hotel_id: str
    name: str                     # "豪华大床房"
    bed_type: str = ""            # 大床/双床
    area_m2: float = 0.0
    max_guests: int = 2
    price: float
    breakfast: bool = False
    cancel_policy: str = ""       # "入住当日18:00前免费取消"
    available_rooms: int = 3
    amenities: list[str] = []


# =============================================================================
# 景点门票
# =============================================================================


class ScenicItem(BaseModel):
    """景区信息。"""
    id: str
    name: str
    city: str
    lat: float
    lng: float
    level: str = ""               # 5A/4A/3A
    avg_rating: float = 0.0
    distance_km: float = 0.0
    open_hours: str = ""
    tags: list[str] = []
    thumbnail: str = ""


class TicketType(BaseModel):
    """门票类型。"""
    id: str
    scenic_id: str
    name: str                     # "成人票"/"学生票"/"亲子套票"
    price: float
    original_price: float = 0.0
    require_id: bool = False      # 是否需要身份证
    available_count: int = 999
    valid_date: str = ""          # 指定日期 or "任意"


# =============================================================================
# 用户
# =============================================================================


class UserAddress(BaseModel):
    """用户地址。"""
    id: str = ""
    user_id: str = ""
    name: str                     # 收货人
    phone: str
    province: str = ""
    city: str = ""
    district: str = ""
    detail: str = ""              # 详细地址
    lat: float = 0.0
    lng: float = 0.0
    tag: str = ""                 # 家/公司/学校
    is_default: bool = False


# =============================================================================
# 通用订单（适配多种订单类型）
# =============================================================================


class OrderItem(BaseModel):
    """通用订单商品行。"""
    item_id: str
    name: str = ""
    quantity: int = 1
    unit_price: float = 0.0
    specs: dict[str, str] = {}    # {规格: 选项}


class CommonOrderDetail(BaseModel):
    """通用订单详情。"""
    order_id: str
    order_type: str               # reservation/takeout/movie/hotel/scenic/coupon
    user_id: str
    poi_id: str = ""
    poi_name: str = ""
    items: list[dict] = []
    total_price: float = 0.0
    paid_amount: float = 0.0
    discount_amount: float = 0.0
    pay_method: str = ""
    status: str = "pending"
    created_at: str = ""
    paid_at: str = ""
    completed_at: str = ""
    cancelled_at: str = ""
    refund_id: str = ""
    remark: str = ""
    can_cancel: bool = True
    can_refund: bool = False
    cancel_reason: str = ""


# =============================================================================
# 天气
# =============================================================================


class WeatherData(BaseModel):
    """天气数据。"""
    city: str
    date: str
    temp_high: int
    temp_low: int
    condition: str                # 晴/多云/阴/小雨等
    humidity: int
    wind_level: int
    aqi: int                      # 空气质量指数
    suitable_for_outdoor: bool


# =============================================================================
# 路线规划
# =============================================================================


class RouteData(BaseModel):
    """路线规划结果。"""
    distance_km: float
    duration_min: int
    mode: str
    polyline: list[list[float]] = []


# =============================================================================
# 工具函数
# =============================================================================


def _make_id(prefix: str = "") -> str:
    """生成唯一 ID。"""
    uid = uuid.uuid4().hex[:12]
    return f"{prefix}_{uid}" if prefix else uid


def _now_iso() -> str:
    """当前 UTC 时间 ISO 格式。"""
    return datetime.now(timezone.utc).isoformat()
