"""C端 收藏/搜索/评价路由."""

from fastapi import APIRouter, Query, Request
from contracts.schemas.common import Result
from contracts.schemas.user.auth import FavoriteAddReq, FavoriteRemoveReq
from contracts.schemas.product.product import ReviewCreateReq

# ── Favorites ──
fav_router = APIRouter(prefix="/favorites")


def _svc(request: Request):
    return request.app.state.commerce_services


@fav_router.get("")
async def list_favorites(request: Request, type: str = Query(default=None)) -> Result:
    auth = request.headers.get("Authorization", "")
    return _svc(request).favorite.list_favorites(auth, type)


@fav_router.post("")
async def add_favorite(req: FavoriteAddReq, request: Request) -> Result:
    auth = request.headers.get("Authorization", "")
    return _svc(request).favorite.toggle(auth, req.target_type, "add", req.target_id)


@fav_router.delete("")
async def remove_favorite(req: FavoriteRemoveReq, request: Request) -> Result:
    auth = request.headers.get("Authorization", "")
    return _svc(request).favorite.toggle(auth, req.target_type, "remove", req.target_id)


# ── Search ──
search_router = APIRouter(prefix="/search")


@search_router.get("")
async def search(request: Request, q: str = Query(min_length=1, max_length=100), type: str = Query(default=None), page: int = Query(default=1, ge=1), size: int = Query(default=20, ge=1, le=100)) -> Result:
    return _svc(request).search.search({"q": q, "type": type, "page": page, "size": size})


@search_router.get("/hot")
async def hot(request: Request) -> Result:
    return _svc(request).search.hot_searches()


@search_router.get("/suggestions")
async def suggestions(request: Request, q: str = Query(min_length=1)) -> Result:
    return _svc(request).search.suggestions(q)


@search_router.get("/history")
async def history(request: Request) -> Result:
    auth = request.headers.get("Authorization", "")
    return _svc(request).search.history(auth)


@search_router.delete("/history")
async def clear_history(request: Request) -> Result:
    auth = request.headers.get("Authorization", "")
    return _svc(request).search.clear_history(auth)


# ── Review ──
review_router = APIRouter(prefix="/reviews")


@review_router.post("")
async def create_review(req: ReviewCreateReq, request: Request) -> Result:
    auth = request.headers.get("Authorization", "")
    return _svc(request).review.create_review(auth, req.model_dump())
