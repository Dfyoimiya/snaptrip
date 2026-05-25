"""Payment domain DTOs — create payment, callback, refund."""

from __future__ import annotations

from pydantic import BaseModel


class PaymentCreateResp(BaseModel):
    order_id: str
    order_no: str
    pay_url: str
    amount: int  # 分


class PaymentCallbackReq(BaseModel):
    order_no: str
    transaction_id: str
    pay_amount: int  # 分
    pay_time: str  # ISO 8601
    status: str  # "SUCCESS" | "FAILED"
    sign: str


class RefundReq(BaseModel):
    order_id: str
    amount: int  # 分, 0=全额退款
    reason: str | None = None


class RefundResp(BaseModel):
    refund_id: str
    order_id: str
    amount: int
    status: str  # "SUCCESS" | "FAILED"
