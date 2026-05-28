"""Mock Server — commerce service layer. Injected into app.state.commerce_services."""

from __future__ import annotations

import hashlib
import json
import math
import random
import time
import uuid
from pathlib import Path

from contracts.schemas.common import PageResult, Result
from contracts.schemas.errors import ErrorCode

import app.state as state

# ── Data helpers ──────────────────────────────────────────────────────────────────

DATA_DIR = Path(__file__).parent.parent.parent / "data"


def _load(name: str) -> list[dict]:
    p = DATA_DIR / name
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else []


def _get_user_id(auth: str) -> str | None:
    if not auth.startswith("Bearer "):
        return None
    token = auth.replace("Bearer ", "")
    session = state._sessions.get(token)
    if not session or session.get("expires_at", 0) < time.time():
        return None
    return session.get("user_id")


def _get_admin_id(auth: str) -> str | None:
    if not auth.startswith("Bearer "):
        return None
    token = auth.replace("Bearer ", "")
    session = state._admin_sessions.get(token)
    if not session or session.get("expires_at", 0) < time.time():
        return None
    return session.get("admin_id")


def _haversine(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng / 2) ** 2
    )
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _ok(data=None):
    return Result(code=0, message="success", data=data)


def _err(code: ErrorCode, message: str | None = None):
    from contracts.schemas.errors import ERROR_META

    msg = message or ERROR_META.get(code, ("未知错误", 400))[0]
    return Result(code=code.value, message=msg, data=None)


# ── User Service ──────────────────────────────────────────────────────────────────


class MockUserService:
    """Mock user auth & profile."""

    def register(self, phone: str, password: str, nickname: str = "") -> Result:
        if not phone or len(phone) != 11:
            return _err(ErrorCode.USER_INVALID_PHONE)
        for u in state._users.values():
            if u.get("phone") == phone:
                return _err(ErrorCode.USER_PHONE_EXISTS)
        uid = state.next_id("U")
        user = {
            "user_id": uid,
            "phone": phone,
            "password_hash": hashlib.sha256(password.encode()).hexdigest(),
            "nickname": nickname or f"用户{uid[-4:]}",
            "avatar": "",
            "gender": 0,
            "created_at": int(time.time()),
        }
        state._users[uid] = user
        return _ok({"user_id": uid, "nickname": user["nickname"]})

    def login(self, phone: str, password: str) -> Result:
        pw_hash = hashlib.sha256(password.encode()).hexdigest()
        for u in state._users.values():
            if u.get("phone") == phone:
                if u.get("password_hash") != pw_hash:
                    return _err(ErrorCode.USER_WRONG_PASSWORD)
                if u.get("status") == "DISABLED":
                    return _err(ErrorCode.USER_ACCOUNT_DISABLED)
                token = uuid.uuid4().hex
                state._sessions[token] = {
                    "user_id": u["user_id"],
                    "expires_at": int(time.time()) + 86400 * 7,
                }
                return _ok({
                    "token": token,
                    "expires_in": 86400 * 7,
                    "user_id": u["user_id"],
                    "nickname": u.get("nickname", ""),
                })
        return _err(ErrorCode.USER_WRONG_PASSWORD)

    def refresh_token(self, refresh_token: str) -> Result:
        session = state._sessions.get(refresh_token)
        if not session or session.get("expires_at", 0) < time.time():
            return _err(ErrorCode.USER_TOKEN_EXPIRED)
        new_token = uuid.uuid4().hex
        session["expires_at"] = int(time.time()) + 86400 * 7
        state._sessions[new_token] = session
        del state._sessions[refresh_token]
        return _ok({"token": new_token, "expires_in": 86400 * 7})

    def logout(self, auth: str) -> Result:
        uid = _get_user_id(auth)
        if not uid:
            return _err(ErrorCode.USER_TOKEN_INVALID)
        token = auth.replace("Bearer ", "")
        state._sessions.pop(token, None)
        return _ok(None)

    def get_profile(self, auth: str) -> Result:
        uid = _get_user_id(auth)
        if not uid:
            return _err(ErrorCode.USER_TOKEN_INVALID)
        user = state._users.get(uid)
        if not user:
            return _err(ErrorCode.USER_TOKEN_INVALID)
        return _ok({
            "user_id": user["user_id"],
            "phone": user["phone"],
            "nickname": user["nickname"],
            "avatar": user.get("avatar", ""),
            "gender": user.get("gender", 0),
        })

    def update_profile(self, auth: str, data: dict) -> Result:
        uid = _get_user_id(auth)
        if not uid:
            return _err(ErrorCode.USER_TOKEN_INVALID)
        user = state._users.get(uid)
        if not user:
            return _err(ErrorCode.USER_TOKEN_INVALID)
        allowed = {"nickname", "avatar", "gender"}
        for k, v in data.items():
            if k in allowed:
                user[k] = v
        return _ok({
            "user_id": user["user_id"],
            "nickname": user["nickname"],
            "avatar": user.get("avatar", ""),
            "gender": user.get("gender", 0),
        })


# ── Home Service ──────────────────────────────────────────────────────────────────


class MockHomeService:
    """Mock home page data."""

    def get_banners(self) -> Result:
        banners = _load("seed_banners.json")
        active = [b for b in banners if b.get("status") == "ACTIVE"]
        active.sort(key=lambda x: x.get("sort_order", 0))
        return _ok(active)

    def get_categories(self) -> Result:
        categories = _load("seed_categories.json")
        return _ok(categories)

    def get_recommend(self, lat: float, lng: float, page: int = 1, size: int = 20) -> Result:
        merchants = _load("seed_merchants.json")
        recs = []
        for m in merchants:
            if m.get("status") != "OPEN":
                continue
            dist = _haversine(lat, lng, m.get("lat", 0), m.get("lng", 0))
            recs.append({**m, "distance_km": round(dist, 2)})
        recs.sort(key=lambda x: (x["distance_km"], -x.get("rating", 0)))
        total = len(recs)
        start = (page - 1) * size
        end = start + size
        page_list = recs[start:end]
        pages = math.ceil(total / size) if size > 0 else 0
        return _ok(PageResult(page=page, size=size, total=total, pages=pages, list=page_list))


# ── Merchant Service ──────────────────────────────────────────────────────────────


class MockMerchantService:
    """Mock merchant & product listing."""

    def list_merchants(self, query: dict) -> Result:
        merchants = _load("seed_merchants.json")
        # Filters
        if q := query.get("keyword"):
            ql = q.lower()
            merchants = [m for m in merchants if ql in m.get("name", "").lower() or ql in m.get("description", "").lower()]
        if cat := query.get("category_id"):
            merchants = [m for m in merchants if m.get("category_id") == cat]
        if status := query.get("status"):
            merchants = [m for m in merchants if m.get("status") == status]
        if tags := query.get("tags"):
            tag_list = tags.split(",")
            merchants = [m for m in merchants if any(t in m.get("tags", []) for t in tag_list)]
        # Sort
        sort_by = query.get("sort_by", "rating")
        sort_order = query.get("sort_order", "desc")
        reverse = sort_order == "desc"
        if sort_by == "distance" and query.get("lat") and query.get("lng"):
            lat, lng = float(query["lat"]), float(query["lng"])
            for m in merchants:
                m["distance_km"] = round(_haversine(lat, lng, m.get("lat", 0), m.get("lng", 0)), 2)
            merchants.sort(key=lambda x: x.get("distance_km", 999))
        elif sort_by in ("rating", "sales"):
            merchants.sort(key=lambda x: x.get(sort_by, 0), reverse=reverse)
        else:
            merchants.sort(key=lambda x: x.get("id", ""))
        # Paginate
        page = int(query.get("page", 1))
        size = int(query.get("size", 20))
        total = len(merchants)
        start = (page - 1) * size
        end = start + size
        page_list = merchants[start:end]
        pages = math.ceil(total / size) if size > 0 else 0
        return _ok(PageResult(page=page, size=size, total=total, pages=pages, list=page_list))

    def get_merchant(self, merchant_id: str) -> Result:
        merchants = _load("seed_merchants.json")
        for m in merchants:
            if m.get("id") == merchant_id:
                return _ok(m)
        return _err(ErrorCode.MERCH_NOT_FOUND)

    def get_product(self, product_id: str) -> Result:
        products = _load("seed_products.json")
        for p in products:
            if p.get("id") == product_id:
                if p.get("status") != "ON_SHELF":
                    return _err(ErrorCode.PROD_OFF_SHELF)
                return _ok(p)
        return _err(ErrorCode.PROD_NOT_FOUND)


# ── Cart Service ──────────────────────────────────────────────────────────────────


class MockCartService:
    """Mock shopping cart."""

    def get_cart(self, auth: str) -> Result:
        uid = _get_user_id(auth)
        if not uid:
            return _err(ErrorCode.USER_TOKEN_INVALID)
        return _ok(state._carts.get(uid, []))

    def add_item(
        self,
        auth: str,
        product_id: str,
        spec_value_id: str | None = None,
        flavor_ids: list[str] | None = None,
        qty: int = 1,
    ) -> Result:
        uid = _get_user_id(auth)
        if not uid:
            return _err(ErrorCode.USER_TOKEN_INVALID)
        products = _load("seed_products.json")
        prod = next((p for p in products if p.get("id") == product_id), None)
        if not prod:
            return _err(ErrorCode.PROD_NOT_FOUND)
        if prod.get("status") != "ON_SHELF":
            return _err(ErrorCode.PROD_OFF_SHELF)
        cart = state._carts.setdefault(uid, [])
        item_id = state.next_id("CI")
        item = {
            "item_id": item_id,
            "product_id": product_id,
            "product_name": prod["name"],
            "product_image": prod.get("image", ""),
            "merchant_id": prod.get("merchant_id", ""),
            "price": prod["price"],
            "spec_value_id": spec_value_id,
            "flavor_ids": flavor_ids or [],
            "qty": qty,
        }
        # Apply spec price offset
        if spec_value_id:
            for spec in prod.get("specs", []):
                for v in spec.get("values", []):
                    if v.get("value_id") == spec_value_id:
                        item["price"] += v.get("price_offset", 0)
        # Apply flavor extra prices
        if flavor_ids:
            for fid in flavor_ids:
                for f in prod.get("flavors", []):
                    if f.get("flavor_id") == fid:
                        item["price"] += f.get("extra_price", 0)
        cart.append(item)
        return _ok(item)

    def update_qty(self, auth: str, item_id: str, qty: int) -> Result:
        uid = _get_user_id(auth)
        if not uid:
            return _err(ErrorCode.USER_TOKEN_INVALID)
        cart = state._carts.get(uid, [])
        for item in cart:
            if item.get("item_id") == item_id:
                item["qty"] = max(1, qty)
                return _ok(item)
        return _err(ErrorCode.CART_ITEM_INVALID)

    def remove_item(self, auth: str, item_id: str) -> Result:
        uid = _get_user_id(auth)
        if not uid:
            return _err(ErrorCode.USER_TOKEN_INVALID)
        cart = state._carts.get(uid, [])
        for i, item in enumerate(cart):
            if item.get("item_id") == item_id:
                cart.pop(i)
                return _ok(None)
        return _err(ErrorCode.CART_ITEM_INVALID)

    def clear(self, auth: str) -> Result:
        uid = _get_user_id(auth)
        if not uid:
            return _err(ErrorCode.USER_TOKEN_INVALID)
        state._carts.pop(uid, None)
        return _ok(None)


# ── Order Service ─────────────────────────────────────────────────────────────────

_VALID_TRANSITIONS = {
    "PENDING": ["PAID", "CANCELLED"],
    "PAID": ["CONFIRMED"],
    "CONFIRMED": ["DELIVERING", "CANCELLED"],
    "DELIVERING": ["COMPLETED"],
    "COMPLETED": [],
    "CANCELLED": [],
}


class MockOrderService:
    """Mock order management."""

    def create_order(self, auth: str, data: dict) -> Result:
        uid = _get_user_id(auth)
        if not uid:
            return _err(ErrorCode.USER_TOKEN_INVALID)
        cart = state._carts.get(uid, [])
        if not cart:
            return _err(ErrorCode.ORDER_CART_EMPTY)
        order_id = state.next_id("ORD")
        order_no = state.gen_order_no()
        items = []
        total_price = 0
        for item in cart:
            order_item_id = state.next_id("OI")
            items.append({
                "order_item_id": order_item_id,
                "order_id": order_id,
                "product_id": item["product_id"],
                "product_name": item["product_name"],
                "product_image": item.get("product_image", ""),
                "price": item["price"],
                "qty": item["qty"],
                "spec_value_id": item.get("spec_value_id"),
                "flavor_ids": item.get("flavor_ids", []),
                "subtotal": item["price"] * item["qty"],
            })
            total_price += item["price"] * item["qty"]
        address_id = data.get("address_id", "")
        remark = data.get("remark", "")
        now_ts = int(time.time())
        order = {
            "order_id": order_id,
            "order_no": order_no,
            "user_id": uid,
            "status": "PENDING",
            "total_price": total_price,
            "actual_price": total_price,
            "address_id": address_id,
            "remark": remark,
            "created_at": now_ts,
            "updated_at": now_ts,
        }
        state._orders[order_id] = order
        state._order_items[order_id] = items
        state._order_status_logs[order_id] = [{
            "log_id": state.next_id("LOG"),
            "order_id": order_id,
            "from_status": "",
            "to_status": "PENDING",
            "operator": uid,
            "remark": "创建订单",
            "created_at": now_ts,
        }]
        state._carts.pop(uid, None)
        return _ok(order)

    def get_order(self, order_id: str) -> Result:
        order = state._orders.get(order_id)
        if not order:
            return _err(ErrorCode.ORDER_NOT_FOUND)
        items = state._order_items.get(order_id, [])
        logs = state._order_status_logs.get(order_id, [])
        return _ok({**order, "items": items, "status_logs": logs})

    def list_orders(self, auth: str, query: dict) -> Result:
        uid = _get_user_id(auth)
        if not uid:
            return _err(ErrorCode.USER_TOKEN_INVALID)
        orders = [o for o in state._orders.values() if o.get("user_id") == uid]
        if status := query.get("status"):
            orders = [o for o in orders if o.get("status") == status]
        orders.sort(key=lambda o: o.get("created_at", 0), reverse=True)
        page = int(query.get("page", 1))
        size = int(query.get("size", 20))
        total = len(orders)
        start = (page - 1) * size
        end = start + size
        page_list = orders[start:end]
        pages = math.ceil(total / size) if size > 0 else 0
        return _ok(PageResult(page=page, size=size, total=total, pages=pages, list=page_list))

    def cancel_order(self, order_id: str, auth: str, reason: str = "") -> Result:
        uid = _get_user_id(auth)
        if not uid:
            return _err(ErrorCode.USER_TOKEN_INVALID)
        order = state._orders.get(order_id)
        if not order:
            return _err(ErrorCode.ORDER_NOT_FOUND)
        if order["status"] != "PENDING":
            return _err(ErrorCode.ORDER_STATUS_INVALID)
        order["status"] = "CANCELLED"
        order["updated_at"] = int(time.time())
        state._order_status_logs.setdefault(order_id, []).append({
            "log_id": state.next_id("LOG"),
            "order_id": order_id,
            "from_status": "PENDING",
            "to_status": "CANCELLED",
            "operator": uid,
            "remark": reason or "用户取消",
            "created_at": int(time.time()),
        })
        return _ok(order)

    def pay_order(self, order_id: str, auth: str) -> Result:
        uid = _get_user_id(auth)
        if not uid:
            return _err(ErrorCode.USER_TOKEN_INVALID)
        order = state._orders.get(order_id)
        if not order:
            return _err(ErrorCode.ORDER_NOT_FOUND)
        if order["status"] != "PENDING":
            return _err(ErrorCode.ORDER_STATUS_INVALID)
        order["status"] = "PAID"
        order["updated_at"] = int(time.time())
        state._order_status_logs.setdefault(order_id, []).append({
            "log_id": state.next_id("LOG"),
            "order_id": order_id,
            "from_status": "PENDING",
            "to_status": "PAID",
            "operator": uid,
            "remark": "用户支付",
            "created_at": int(time.time()),
        })
        return _ok(order)

    def update_status(self, order_id: str, target_status: str, operator: str, remark: str = "") -> Result:
        order = state._orders.get(order_id)
        if not order:
            return _err(ErrorCode.ORDER_NOT_FOUND)
        current = order["status"]
        allowed = _VALID_TRANSITIONS.get(current, [])
        if target_status not in allowed:
            return _err(ErrorCode.ORDER_STATUS_INVALID)
        old_status = current
        order["status"] = target_status
        order["updated_at"] = int(time.time())
        state._order_status_logs.setdefault(order_id, []).append({
            "log_id": state.next_id("LOG"),
            "order_id": order_id,
            "from_status": old_status,
            "to_status": target_status,
            "operator": operator,
            "remark": remark or f"状态变更: {old_status}→{target_status}",
            "created_at": int(time.time()),
        })
        return _ok(order)


# ── Address Service ───────────────────────────────────────────────────────────────


class MockAddressService:
    """Mock shipping addresses."""

    def list_addresses(self, auth: str) -> Result:
        uid = _get_user_id(auth)
        if not uid:
            return _err(ErrorCode.USER_TOKEN_INVALID)
        return _ok(state._addresses.get(uid, []))

    def create_address(self, auth: str, data: dict) -> Result:
        uid = _get_user_id(auth)
        if not uid:
            return _err(ErrorCode.USER_TOKEN_INVALID)
        addrs = state._addresses.setdefault(uid, [])
        if len(addrs) >= 20:
            return _err(ErrorCode.ADDR_LIMIT_REACHED)
        addr_id = state.next_id("ADDR")
        addr = {
            "address_id": addr_id,
            "user_id": uid,
            "name": data.get("name", ""),
            "phone": data.get("phone", ""),
            "province": data.get("province", ""),
            "city": data.get("city", ""),
            "district": data.get("district", ""),
            "detail": data.get("detail", ""),
            "label": data.get("label", ""),
            "lat": data.get("lat", 0),
            "lng": data.get("lng", 0),
            "is_default": len(addrs) == 0,
            "created_at": int(time.time()),
        }
        addrs.append(addr)
        return _ok(addr)

    def update_address(self, auth: str, address_id: str, data: dict) -> Result:
        uid = _get_user_id(auth)
        if not uid:
            return _err(ErrorCode.USER_TOKEN_INVALID)
        addrs = state._addresses.get(uid, [])
        for a in addrs:
            if a.get("address_id") == address_id:
                updatable = {"name", "phone", "province", "city", "district", "detail", "label", "lat", "lng"}
                for k, v in data.items():
                    if k in updatable:
                        a[k] = v
                return _ok(a)
        return _err(ErrorCode.ADDR_NOT_FOUND)

    def delete_address(self, auth: str, address_id: str) -> Result:
        uid = _get_user_id(auth)
        if not uid:
            return _err(ErrorCode.USER_TOKEN_INVALID)
        addrs = state._addresses.get(uid, [])
        for i, a in enumerate(addrs):
            if a.get("address_id") == address_id:
                addrs.pop(i)
                return _ok(None)
        return _err(ErrorCode.ADDR_NOT_FOUND)

    def set_default(self, auth: str, address_id: str) -> Result:
        uid = _get_user_id(auth)
        if not uid:
            return _err(ErrorCode.USER_TOKEN_INVALID)
        addrs = state._addresses.get(uid, [])
        found = False
        for a in addrs:
            if a.get("address_id") == address_id:
                a["is_default"] = True
                found = True
            else:
                a["is_default"] = False
        if not found:
            return _err(ErrorCode.ADDR_NOT_FOUND)
        return _ok(None)


# ── Favorite Service ──────────────────────────────────────────────────────────────


class MockFavoriteService:
    """Mock user favorites."""

    def list_favorites(self, auth: str, target_type: str = "") -> Result:
        uid = _get_user_id(auth)
        if not uid:
            return _err(ErrorCode.USER_TOKEN_INVALID)
        favs = state._favorites.get(uid, [])
        if target_type:
            favs = [f for f in favs if f.get("target_type") == target_type]
        return _ok(favs)

    def toggle(self, auth: str, target_type: str, action: str, target_id: str) -> Result:
        uid = _get_user_id(auth)
        if not uid:
            return _err(ErrorCode.USER_TOKEN_INVALID)
        favs = state._favorites.setdefault(uid, [])
        if action == "add":
            existing = any(f.get("target_id") == target_id and f.get("target_type") == target_type for f in favs)
            if not existing:
                favs.append({
                    "favorite_id": state.next_id("FAV"),
                    "user_id": uid,
                    "target_type": target_type,
                    "target_id": target_id,
                    "created_at": int(time.time()),
                })
            return _ok({"is_favorited": True})
        elif action == "remove":
            for i, f in enumerate(favs):
                if f.get("target_id") == target_id and f.get("target_type") == target_type:
                    favs.pop(i)
                    break
            return _ok({"is_favorited": False})
        return _ok({"is_favorited": False})


# ── Search Service ────────────────────────────────────────────────────────────────


class MockSearchService:
    """Mock search."""

    def search(self, query: dict) -> Result:
        keyword = query.get("keyword", "").strip()
        if not keyword:
            return _err(ErrorCode.SRCH_KEYWORD_EMPTY)
        if len(keyword) > 50:
            return _err(ErrorCode.SRCH_KEYWORD_TOO_LONG)
        kl = keyword.lower()
        merchants = _load("seed_merchants.json")
        products = _load("seed_products.json")
        m_results = [
            {**m, "result_type": "merchant"}
            for m in merchants
            if m.get("status") == "OPEN" and (kl in m.get("name", "").lower() or kl in (m.get("description", "") or "").lower()
                                              or any(kl in t.lower() for t in m.get("tags", [])))
        ]
        p_results = [
            {**p, "result_type": "product"}
            for p in products
            if p.get("status") == "ON_SHELF" and (kl in p.get("name", "").lower() or kl in (p.get("description", "") or "").lower())
        ]
        results = m_results + p_results
        return _ok(results)

    def hot_searches(self) -> Result:
        data = _load("seed_hot_searches.json")
        return _ok(data)

    def suggestions(self, q: str) -> Result:
        if not q:
            return _ok([])
        ql = q.lower()
        merchants = _load("seed_merchants.json")
        products = _load("seed_products.json")
        names = set()
        for m in merchants:
            if ql in m.get("name", "").lower():
                names.add(m["name"])
        for p in products:
            if ql in p.get("name", "").lower():
                names.add(p["name"])
        return _ok(list(names)[:10])

    def history(self, auth: str) -> Result:
        uid = _get_user_id(auth)
        if not uid:
            return _err(ErrorCode.USER_TOKEN_INVALID)
        hist = state._search_history.get(uid, [])
        hist.sort(key=lambda x: x.get("created_at", 0), reverse=True)
        return _ok(hist)

    def clear_history(self, auth: str) -> Result:
        uid = _get_user_id(auth)
        if not uid:
            return _err(ErrorCode.USER_TOKEN_INVALID)
        state._search_history.pop(uid, None)
        return _ok(None)


# ── Review Service ────────────────────────────────────────────────────────────────


class MockReviewService:
    """Mock product reviews."""

    def create_review(self, auth: str, data: dict) -> Result:
        uid = _get_user_id(auth)
        if not uid:
            return _err(ErrorCode.USER_TOKEN_INVALID)
        rating = data.get("rating", 0)
        if not isinstance(rating, int) or rating < 1 or rating > 5:
            return _err(ErrorCode.REVW_INVALID_RATING)
        review_id = state.next_id("REV")
        user = state._users.get(uid, {})
        review = {
            "id": review_id,
            "user_id": uid,
            "user_nickname": user.get("nickname", ""),
            "user_avatar": user.get("avatar", ""),
            "product_id": data.get("product_id", ""),
            "order_id": data.get("order_id", ""),
            "rating": rating,
            "content": data.get("content", ""),
            "images": data.get("images", []),
            "created_at": int(time.time()),
        }
        state._reviews.append(review)
        return _ok(review)

    def list_reviews(self, product_id: str = "", page: int = 1, size: int = 20) -> Result:
        reviews = state._reviews.copy()
        seed_reviews = _load("seed_reviews.json")
        for r in seed_reviews:
            if not any(ex.get("id") == r.get("id") for ex in reviews):
                reviews.append(r)
        if product_id:
            reviews = [r for r in reviews if r.get("product_id") == product_id]
        reviews.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        total = len(reviews)
        start = (page - 1) * size
        end = start + size
        page_list = reviews[start:end]
        pages = math.ceil(total / size) if size > 0 else 0
        return _ok(PageResult(page=page, size=size, total=total, pages=pages, list=page_list))

    def get_stats(self, product_id: str) -> Result:
        reviews = state._reviews.copy()
        seed_reviews = _load("seed_reviews.json")
        for r in seed_reviews:
            if not any(ex.get("id") == r.get("id") for ex in reviews):
                reviews.append(r)
        prods = [r for r in reviews if r.get("product_id") == product_id]
        if not prods:
            return _ok({"total": 0, "avg_rating": 0, "distribution": {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}})
        total = len(prods)
        avg = round(sum(r["rating"] for r in prods) / total, 1)
        dist = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        for r in prods:
            dist[r["rating"]] = dist.get(r["rating"], 0) + 1
        return _ok({"total": total, "avg_rating": avg, "distribution": dist})


# ── Admin Service ─────────────────────────────────────────────────────────────────


class MockAdminService:
    """Mock admin panel."""

    def admin_login(self, username: str, password: str) -> Result:
        admins = _load("seed_admin_users.json")
        for a in admins:
            if a.get("username") == username:
                if a.get("password") != password:
                    return _err(ErrorCode.AUTH_WRONG_CREDENTIALS)
                if a.get("status") != "ACTIVE":
                    return _err(ErrorCode.AUTH_ACCOUNT_DISABLED)
                token = uuid.uuid4().hex
                state._admin_sessions[token] = {
                    "admin_id": a["id"],
                    "username": a["username"],
                    "roles": a.get("roles", []),
                    "permissions": a.get("permissions", []),
                    "expires_at": int(time.time()) + 86400,
                }
                return _ok({
                    "token": token,
                    "admin_id": a["id"],
                    "username": a["username"],
                    "real_name": a.get("real_name", ""),
                    "roles": a.get("roles", []),
                    "permissions": a.get("permissions", []),
                })
        return _err(ErrorCode.AUTH_WRONG_CREDENTIALS)

    def get_dashboard(self) -> Result:
        orders = list(state._orders.values())
        users = list(state._users.values())
        today_revenue = sum(o.get("actual_price", 0) for o in orders if o.get("status") not in ("CANCELLED",))
        return _ok({
            "total_users": len(users),
            "total_orders": len(orders),
            "today_revenue": today_revenue,
            "pending_orders": sum(1 for o in orders if o.get("status") == "PENDING"),
            "delivering_orders": sum(1 for o in orders if o.get("status") == "DELIVERING"),
        })

    def list_employees(self, page: int = 1, size: int = 20) -> Result:
        admins = _load("seed_admin_users.json")
        total = len(admins)
        start = (page - 1) * size
        end = start + size
        page_list = admins[start:end]
        pages = math.ceil(total / size) if size > 0 else 0
        return _ok(PageResult(page=page, size=size, total=total, pages=pages, list=page_list))

    def create_employee(self, data: dict) -> Result:
        eid = state.next_id("ADMIN")
        emp = {
            "id": eid,
            "username": data.get("username", ""),
            "password": data.get("password", ""),
            "real_name": data.get("real_name", ""),
            "phone": data.get("phone", ""),
            "status": "ACTIVE",
            "roles": data.get("roles", []),
            "permissions": data.get("permissions", []),
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        return _ok(emp)

    def update_employee(self, employee_id: str, data: dict) -> Result:
        admins = _load("seed_admin_users.json")
        for a in admins:
            if a.get("id") == employee_id:
                a.update({k: v for k, v in data.items() if k in ("username", "real_name", "phone", "status", "roles", "permissions")})
                return _ok(a)
        return _err(ErrorCode.ADMIN_NO_OP_PERMISSION)

    def delete_employee(self, employee_id: str, auth: str) -> Result:
        admin_id = _get_admin_id(auth)
        if employee_id == admin_id:
            return _err(ErrorCode.ADMIN_CANNOT_DELETE_SELF)
        # Check seed data
        admins = _load("seed_admin_users.json")
        for a in admins:
            if a.get("id") == employee_id:
                return _ok(None)
        return _err(ErrorCode.ADMIN_NO_OP_PERMISSION)

    def assign_roles(self, employee_id: str, role_codes: list[str]) -> Result:
        admins = _load("seed_admin_users.json")
        for a in admins:
            if a.get("id") == employee_id:
                a["roles"] = role_codes
                return _ok(a)
        return _err(ErrorCode.ADMIN_NO_OP_PERMISSION)

    def list_roles(self, page: int = 1, size: int = 20) -> Result:
        roles = _load("seed_roles.json")
        total = len(roles)
        start = (page - 1) * size
        end = start + size
        page_list = roles[start:end]
        pages = math.ceil(total / size) if size > 0 else 0
        return _ok(PageResult(page=page, size=size, total=total, pages=pages, list=page_list))

    def create_role(self, data: dict) -> Result:
        rid = state.next_id("ROLE")
        role = {
            "id": rid,
            "role_code": data.get("role_code", ""),
            "role_name": data.get("role_name", ""),
            "description": data.get("description", ""),
            "permission_codes": data.get("permission_codes", []),
        }
        return _ok(role)

    def assign_permissions(self, role_id: str, permission_codes: list[str]) -> Result:
        roles = _load("seed_roles.json")
        for r in roles:
            if r.get("id") == role_id:
                r["permission_codes"] = permission_codes
                return _ok(r)
        return _err(ErrorCode.ADMIN_NO_OP_PERMISSION)

    def get_permission_tree(self) -> Result:
        tree = [
            {"code": "dashboard", "name": "仪表盘", "children": [
                {"code": "dashboard:view", "name": "查看仪表盘"},
            ]},
            {"code": "employee", "name": "员工管理", "children": [
                {"code": "employee:list", "name": "查看员工列表"},
                {"code": "employee:create", "name": "添加员工"},
                {"code": "employee:edit", "name": "编辑员工"},
                {"code": "employee:delete", "name": "删除员工"},
            ]},
            {"code": "merchant", "name": "商家管理", "children": [
                {"code": "merchant:list", "name": "查看商家列表"},
                {"code": "merchant:audit", "name": "审核商家"},
                {"code": "merchant:status", "name": "修改商家状态"},
            ]},
            {"code": "category", "name": "分类管理", "children": [
                {"code": "category:list", "name": "查看分类"},
                {"code": "category:create", "name": "添加分类"},
                {"code": "category:edit", "name": "编辑分类"},
                {"code": "category:delete", "name": "删除分类"},
            ]},
            {"code": "product", "name": "商品管理", "children": [
                {"code": "product:list", "name": "查看商品列表"},
                {"code": "product:create", "name": "添加商品"},
                {"code": "product:edit", "name": "编辑商品"},
                {"code": "product:status", "name": "上下架"},
            ]},
            {"code": "order", "name": "订单管理", "children": [
                {"code": "order:list", "name": "查看订单"},
                {"code": "order:status", "name": "修改订单状态"},
                {"code": "order:export", "name": "导出订单"},
            ]},
            {"code": "banner", "name": "Banner管理", "children": [
                {"code": "banner:list", "name": "查看轮播图"},
                {"code": "banner:create", "name": "添加轮播图"},
                {"code": "banner:edit", "name": "编辑轮播图"},
                {"code": "banner:delete", "name": "删除轮播图"},
            ]},
            {"code": "notice", "name": "公告管理", "children": [
                {"code": "notice:list", "name": "查看公告"},
                {"code": "notice:create", "name": "创建公告"},
                {"code": "notice:delete", "name": "删除公告"},
            ]},
            {"code": "stats", "name": "数据统计", "children": [
                {"code": "stats:revenue", "name": "营收统计"},
                {"code": "stats:orders", "name": "订单统计"},
                {"code": "stats:users", "name": "用户统计"},
                {"code": "stats:ranking", "name": "商品排行"},
            ]},
            {"code": "upload", "name": "文件上传", "children": [
                {"code": "upload:image", "name": "上传图片"},
            ]},
        ]
        return _ok(tree)

    def audit_merchant(self, merchant_id: str, audit_status: str, remark: str = "") -> Result:
        merchants = _load("seed_merchants.json")
        for m in merchants:
            if m.get("id") == merchant_id:
                m["audit_status"] = audit_status
                m["audit_remark"] = remark
                return _ok(m)
        return _err(ErrorCode.MERCH_NOT_FOUND)

    def update_merchant_status(self, merchant_id: str, status: str) -> Result:
        merchants = _load("seed_merchants.json")
        for m in merchants:
            if m.get("id") == merchant_id:
                m["status"] = status
                return _ok(m)
        return _err(ErrorCode.MERCH_NOT_FOUND)

    def get_category_tree(self) -> Result:
        categories = _load("seed_categories.json")
        return _ok(categories)

    def create_category(self, data: dict) -> Result:
        cid = state.next_id("CAT")
        cat = {
            "id": cid,
            "name": data.get("name", ""),
            "icon": data.get("icon", ""),
            "type": data.get("type", "PRODUCT"),
            "parent_id": data.get("parent_id"),
            "sort_order": data.get("sort_order", 99),
            "children": [],
        }
        return _ok(cat)

    def update_category(self, category_id: str, data: dict) -> Result:
        return _ok({"id": category_id, **data})

    def delete_category(self, category_id: str) -> Result:
        return _ok(None)

    def list_products_admin(self, query: dict) -> Result:
        products = _load("seed_products.json")
        if q := query.get("keyword"):
            ql = q.lower()
            products = [p for p in products if ql in p.get("name", "").lower()]
        if merchant_id := query.get("merchant_id"):
            products = [p for p in products if p.get("merchant_id") == merchant_id]
        if status := query.get("status"):
            products = [p for p in products if p.get("status") == status]
        if category_id := query.get("category_id"):
            products = [p for p in products if p.get("category_id") == category_id]
        page = int(query.get("page", 1))
        size = int(query.get("size", 20))
        total = len(products)
        start = (page - 1) * size
        end = start + size
        page_list = products[start:end]
        pages = math.ceil(total / size) if size > 0 else 0
        return _ok(PageResult(page=page, size=size, total=total, pages=pages, list=page_list))

    def create_product(self, data: dict) -> Result:
        pid = state.next_id("PROD")
        product = {
            "id": pid,
            "merchant_id": data.get("merchant_id", ""),
            "category_id": data.get("category_id", ""),
            "name": data.get("name", ""),
            "description": data.get("description", ""),
            "image": data.get("image", ""),
            "price": data.get("price", 0),
            "original_price": data.get("original_price"),
            "stock": data.get("stock", 0),
            "sales": 0,
            "rating": 0,
            "status": "ON_SHELF",
            "has_specs": bool(data.get("specs")),
            "specs": data.get("specs", []),
            "flavors": data.get("flavors", []),
            "category_name": data.get("category_name", ""),
        }
        return _ok(product)

    def update_product(self, product_id: str, data: dict) -> Result:
        products = _load("seed_products.json")
        for p in products:
            if p.get("id") == product_id:
                p.update({k: v for k, v in data.items() if k in ("name", "description", "image", "price", "original_price", "stock", "specs", "flavors", "category_id", "category_name")})
                return _ok(p)
        return _err(ErrorCode.PROD_NOT_FOUND)

    def toggle_product_status(self, product_id: str) -> Result:
        products = _load("seed_products.json")
        for p in products:
            if p.get("id") == product_id:
                p["status"] = "OFF_SHELF" if p.get("status") == "ON_SHELF" else "ON_SHELF"
                return _ok(p)
        return _err(ErrorCode.PROD_NOT_FOUND)

    def batch_product_status(self, product_ids: list[str], status: str) -> Result:
        products = _load("seed_products.json")
        updated = []
        for pid in product_ids:
            for p in products:
                if p.get("id") == pid:
                    p["status"] = status
                    updated.append(pid)
        return _ok({"count": len(updated), "product_ids": updated})

    def list_orders_admin(self, query: dict) -> Result:
        orders = list(state._orders.values())
        if status := query.get("status"):
            orders = [o for o in orders if o.get("status") == status]
        if order_no := query.get("order_no"):
            orders = [o for o in orders if order_no in o.get("order_no", "")]
        orders.sort(key=lambda o: o.get("created_at", 0), reverse=True)
        page = int(query.get("page", 1))
        size = int(query.get("size", 20))
        total = len(orders)
        start = (page - 1) * size
        end = start + size
        page_list = orders[start:end]
        pages = math.ceil(total / size) if size > 0 else 0
        return _ok(PageResult(page=page, size=size, total=total, pages=pages, list=page_list))

    def export_orders(self, query: dict) -> Result:
        orders = list(state._orders.values())
        return _ok({"url": f"/exports/orders_{int(time.time())}.csv", "count": len(orders)})

    def list_banners(self, page: int = 1, size: int = 20) -> Result:
        banners = _load("seed_banners.json")
        total = len(banners)
        start = (page - 1) * size
        end = start + size
        page_list = banners[start:end]
        pages = math.ceil(total / size) if size > 0 else 0
        return _ok(PageResult(page=page, size=size, total=total, pages=pages, list=page_list))

    def create_banner(self, data: dict) -> Result:
        bid = state.next_id("BAN")
        banner = {
            "id": bid,
            "image_url": data.get("image_url", ""),
            "link_type": data.get("link_type", "none"),
            "link_id": data.get("link_id"),
            "sort_order": data.get("sort_order", 99),
            "status": "ACTIVE",
        }
        return _ok(banner)

    def update_banner(self, banner_id: str, data: dict) -> Result:
        banners = _load("seed_banners.json")
        for b in banners:
            if b.get("id") == banner_id:
                b.update({k: v for k, v in data.items() if k in ("image_url", "link_type", "link_id", "sort_order", "status")})
                return _ok(b)
        return _ok({"id": banner_id, **data})

    def delete_banner(self, banner_id: str) -> Result:
        return _ok(None)

    def list_notices(self, page: int = 1, size: int = 20) -> Result:
        notices = _load("seed_notices.json")
        total = len(notices)
        start = (page - 1) * size
        end = start + size
        page_list = notices[start:end]
        pages = math.ceil(total / size) if size > 0 else 0
        return _ok(PageResult(page=page, size=size, total=total, pages=pages, list=page_list))

    def create_notice(self, data: dict) -> Result:
        nid = state.next_id("NOT")
        notice = {
            "id": nid,
            "title": data.get("title", ""),
            "content": data.get("content", ""),
            "target_type": data.get("target_type", "ALL"),
            "status": "ACTIVE",
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        return _ok(notice)

    def delete_notice(self, notice_id: str) -> Result:
        return _ok(None)

    def upload_image(self) -> Result:
        return _ok({"url": f"https://dummyimage.com/400x300/{random.randint(0,0xFFFFFF):06x}/fff&text=Upload"})


# ── Statistics Service ────────────────────────────────────────────────────────────


class MockStatisticsService:
    """Mock statistics with generated data."""

    def get_revenue_stats(self, start: str, end: str) -> Result:
        now = time.time()
        days = max(1, random.randint(5, 30))
        daily = []
        total = 0
        for i in range(days):
            ts = now - (days - 1 - i) * 86400
            revenue = random.randint(5000, 50000)
            total += revenue
            daily.append({
                "date": time.strftime("%Y-%m-%d", time.localtime(ts)),
                "revenue": revenue,
                "order_count": random.randint(10, 200),
            })
        return _ok({"total_revenue": total, "daily": daily, "start": start, "end": end})

    def get_order_stats(self, start: str, end: str) -> Result:
        status_counts = {
            "PENDING": random.randint(0, 50),
            "PAID": random.randint(10, 100),
            "CONFIRMED": random.randint(5, 80),
            "DELIVERING": random.randint(5, 60),
            "COMPLETED": random.randint(50, 500),
            "CANCELLED": random.randint(0, 30),
        }
        total = sum(status_counts.values())
        return _ok({
            "total": total,
            "status_distribution": status_counts,
            "avg_order_value": random.randint(3000, 8000),
            "start": start,
            "end": end,
        })

    def get_user_stats(self, start: str, end: str) -> Result:
        now = time.time()
        days = max(1, random.randint(5, 30))
        daily = []
        total_new = 0
        for i in range(days):
            ts = now - (days - 1 - i) * 86400
            new_users = random.randint(0, 100)
            total_new += new_users
            daily.append({
                "date": time.strftime("%Y-%m-%d", time.localtime(ts)),
                "new_users": new_users,
                "active_users": new_users + random.randint(50, 500),
                "paying_users": random.randint(5, 50),
            })
        return _ok({
            "total_users": len(state._users),
            "new_users": total_new,
            "daily": daily,
            "start": start,
            "end": end,
        })

    def get_product_ranking(self, start: str, end: str, limit: int = 10) -> Result:
        products = _load("seed_products.json")
        ranking = []
        for p in products:
            ranking.append({
                "product_id": p["id"],
                "product_name": p["name"],
                "merchant_id": p.get("merchant_id", ""),
                "sales": p.get("sales", 0) + random.randint(-100, 200),
                "revenue": (p.get("sales", 0) + random.randint(-100, 200)) * p.get("price", 0),
                "rating": p.get("rating", 0),
            })
        ranking.sort(key=lambda x: x["sales"], reverse=True)
        return _ok({"ranking": ranking[:limit], "start": start, "end": end})


# ── Aggregate Service ─────────────────────────────────────────────────────────────


class MockCommerceServices:
    """Injected into app.state.commerce_services by main.py."""

    def __init__(self):
        self.user = MockUserService()
        self.home = MockHomeService()
        self.merchant = MockMerchantService()
        self.cart = MockCartService()
        self.order = MockOrderService()
        self.address = MockAddressService()
        self.favorite = MockFavoriteService()
        self.search = MockSearchService()
        self.review = MockReviewService()
        self.admin = MockAdminService()
        self.statistics = MockStatisticsService()


__all__ = ["MockCommerceServices"]
