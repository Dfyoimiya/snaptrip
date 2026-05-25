"""Mock-only DTOs for external service simulation (geo, sms, delivery)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


# ── Geo ──

class GeocodeReq(BaseModel):
    address: str
    city: str | None = None


class GeocodeResp(BaseModel):
    lng: float
    lat: float
    formatted_address: str
    confidence: float = 1.0


class RouteReq(BaseModel):
    from_lng: float
    from_lat: float
    to_lng: float
    to_lat: float
    mode: Literal["walk", "drive", "transit"] = "walk"


class RouteResp(BaseModel):
    distance_km: float
    duration_min: int
    mode: str
    polyline: list[list[float]] = []


class DistanceReq(BaseModel):
    origins: list[tuple[float, float]]          # [[lng, lat], ...]
    destination: tuple[float, float]            # [lng, lat]


class DistanceResp(BaseModel):
    distances: list[float]                      # km per origin


# ── SMS ──

class SmsSendReq(BaseModel):
    phone: str = Field(pattern=r"^1[3-9]\d{9}$")
    scene: str = "login"                        # "login" | "register" | "reset_password"


class SmsVerifyReq(BaseModel):
    phone: str = Field(pattern=r"^1[3-9]\d{9}$")
    code: str = Field(min_length=4, max_length=6)
    scene: str = "login"


# ── Delivery ──

class DeliveryScheduleReq(BaseModel):
    expected_time: str                          # ISO 8601
    item_type: str
    from_poi_id: str
    to_address_id: str
    recipient_phone: str


class DeliveryScheduleResp(BaseModel):
    delivery_id: str
    item_type: str
    expected_time: str
    estimated_arrival: str
    fee: int                                    # 分
    status: str = "SCHEDULED"


class DeliveryTrackResp(BaseModel):
    time: str                                   # ISO 8601
    status: str
    description: str
    location: str | None = None


# ── POI (existing) ──

class PoiSearchReq(BaseModel):
    lat: float = 39.9
    lng: float = 116.4
    radius: float = 15.0
    keyword: str = ""
    category: str = ""
    group_type: str = ""
    limit: int = Field(default=10, ge=1, le=50)


class PoiResp(BaseModel):
    id: str
    name: str
    city: str
    lat: float
    lng: float
    category: str
    tags: list[str] = []
    avg_rating: float
    price_level: int
    distance_km: float | None = None
    open_hours: str = ""


class QueueReq(BaseModel):
    poi_id: str
    date: str = ""
    party_size: int = 2


class QueueResp(BaseModel):
    poi_id: str
    wait_minutes: int
    can_take_number_online: bool
    available_slots: list[str] = []
    queue_length: int = 0


class WeatherReq(BaseModel):
    city: str = "北京"
    date: str = ""


class WeatherResp(BaseModel):
    city: str
    date: str
    temp_high: int
    temp_low: int
    condition: str
    humidity: int
    wind_level: int
    aqi: int
    suitable_for_outdoor: bool
