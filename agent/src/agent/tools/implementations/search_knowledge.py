"""Search knowledge tool — look up FAQ and store policy information.

Since there is no dedicated FAQ/marketplace knowledge API yet, this tool
returns structured policy information from hardcoded templates. This is
acceptable for MVP; a future version will query a vector-backed knowledge base.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from agent.tools.implementations.base import SmartDayBaseTool, ToolResult
from agent.tools.transaction.compensation import CompensationAction

# ── Knowledge base: store policies ───────────────────────────────────────────

POLICIES: dict[str, str] = {
    "shipping": (
        "【配送政策】\n"
        "1. 全国包邮（港澳台及偏远地区除外）。\n"
        "2. 现货商品下单后24小时内发货，预售商品按页面标注时间发货。\n"
        "3. 默认合作快递为顺丰、中通、圆通，不支持指定快递。\n"
        "4. 发货后系统自动推送物流单号，可在订单详情查看物流轨迹。\n"
        "5. 如遇节假日或大促，发货时效可能顺延1-3天。"
    ),
    "returns": (
        "【退换货政策】\n"
        "1. 支持7天无理由退货（商品完好、不影响二次销售）。\n"
        "2. 以下商品不支持无理由退货：生鲜易腐、定制商品、已拆封的数字化商品。\n"
        "3. 退货需在确认收货后7天内申请，超时系统将自动关闭退货入口。\n"
        "4. 退货运费由用户承担（质量问题除外，质量问题由商家承担）。\n"
        "5. 退款将在收到退货并验收通过后1-3个工作日内原路返回。\n"
        "6. 换货需先提交申请，审核通过后寄回商品，收到后2个工作日内发出新商品。"
    ),
    "payment": (
        "【支付方式】\n"
        "1. 支持微信支付、支付宝、银行卡支付。\n"
        "2. 支持分期付款（花呗、信用卡分期），具体期数和手续费以支付页面为准。\n"
        "3. 订单生成后需在30分钟内完成支付，超时订单将自动取消。\n"
        "4. 如遇支付失败，请检查：① 账户余额是否充足 ② 是否超出单笔/单日限额 ③ 网络是否正常。\n"
        "5. 支付成功后可在订单列表查看支付状态，如有异常请联系客服。"
    ),
    "account": (
        "【账户相关】\n"
        "1. 注册账号需绑定手机号，一个手机号只能注册一个账号。\n"
        "2. 可通过手机号+验证码或账号+密码登录。\n"
        "3. 忘记密码可通过绑定的手机号重置。\n"
        "4. 会员等级分为普通会员、银卡会员、金卡会员、钻石会员，消费累积成长值自动升级。\n"
        "5. 积分可抵扣现金，100积分=1元，积分有效期为获得后次年年底。\n"
        "6. 账号注销后所有数据将被清除且不可恢复，请谨慎操作。"
    ),
    "products": (
        "【商品相关】\n"
        "1. 商品价格以结算页面为准，可能因促销活动实时变动。\n"
        "2. 商品图片仅供参考，以实物为准。\n"
        "3. 商品库存实时更新，加入购物车不代表锁定库存，以提交订单时为准。\n"
        "4. 限购商品每人/每ID限购数量详见商品详情页。\n"
        "5. 如发现商品信息错误（价格、规格等），平台有权取消订单并通知用户。"
    ),
}

CATEGORY_ALIASES: dict[str, str] = {
    "ship": "shipping",
    "delivery": "shipping",
    "物流": "shipping",
    "快递": "shipping",
    "return": "returns",
    "refund": "returns",
    "退货": "returns",
    "退款": "returns",
    "换货": "returns",
    "exchange": "returns",
    "pay": "payment",
    "支付": "payment",
    "付款": "payment",
    "account": "account",
    "账户": "account",
    "登录": "account",
    "login": "account",
    "注册": "account",
    "register": "account",
    "积分": "account",
    "会员": "account",
    "product": "products",
    "商品": "products",
    "库存": "products",
    "限购": "products",
    "价格": "products",
}


class SearchKnowledgeArgs(BaseModel):
    query: str = Field(..., description="Question or search query")
    category: str | None = Field(None, description="Optional: 'shipping', 'returns', 'payment', 'account', 'products'")


class SearchKnowledgeTool(SmartDayBaseTool):
    name: str = "search_knowledge"
    description: str = "Search FAQ and knowledge base for answers to general questions about shipping, returns, payment, account, or products"
    is_read_only: bool = True
    cost_model: str = "free"
    args_schema: type[BaseModel] = SearchKnowledgeArgs
    tool_timeout: float = 5.0

    async def _arun(self, **kwargs: Any) -> dict:
        query: str = kwargs.get("query", "")
        category: str | None = kwargs.get("category")

        # Resolve category — check explicit category first, then keyword match
        resolved: list[str] = []
        if category and category in POLICIES:
            resolved.append(category)
        else:
            # Try alias matching on explicit category
            if category and category in CATEGORY_ALIASES:
                resolved.append(CATEGORY_ALIASES[category])
            # Keyword matching on query string
            query_lower = query.lower()
            for keyword, cat in CATEGORY_ALIASES.items():
                if keyword.lower() in query_lower and cat not in resolved:
                    resolved.append(cat)

        # Fallback: return all categories if nothing matched
        if not resolved:
            resolved = list(POLICIES)

        # Build result
        results: dict[str, str] = {}
        for cat in resolved:
            results[cat] = POLICIES.get(cat, "")

        return {"query": query, "matched_categories": resolved, "results": results}

    def compensation(self, args: dict[str, Any], result: ToolResult) -> CompensationAction:
        return self._noop_compensation(
            action_id=self._idem_key(args),
            tool_name=self.name,
        )
