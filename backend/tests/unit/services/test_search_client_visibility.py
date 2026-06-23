"""商品搜索索引可见性规则测试。"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest


@pytest.mark.asyncio
async def test_search_products_filters_unpublished_and_unverified_products() -> None:
    """C 端关键词搜索只能返回已上架且审核通过的商品。"""
    from app.search.client import ESSearchClient

    client = ESSearchClient()
    client._initialized = True
    client._available = True
    client._client = AsyncMock()
    client._client.search.return_value = {
        "hits": {
            "hits": [],
            "total": {"value": 0},
        }
    }

    await client.search_products(keyword="测试商品")

    body = client._client.search.await_args.kwargs["body"]
    filters = body["query"]["bool"]["filter"]
    assert {"term": {"publish_status": 1}} in filters
    assert {"term": {"verify_status": 1}} in filters


@pytest.mark.asyncio
async def test_index_product_waits_for_search_refresh() -> None:
    """B 端保存成功返回前，商品搜索索引应已刷新。"""
    from app.search.client import ESSearchClient

    client = ESSearchClient()
    client._initialized = True
    client._available = True
    client._client = AsyncMock()

    result = await client.index_product("product-id", {"name": "测试商品"})

    assert result is True
    client._client.index.assert_awaited_once_with(
        index=client._index_products,
        id="product-id",
        document={"name": "测试商品"},
        refresh="wait_for",
    )


@pytest.mark.asyncio
async def test_delete_product_waits_for_search_refresh() -> None:
    """B 端删除成功返回前，商品应已从搜索索引移除。"""
    from app.search.client import ESSearchClient

    client = ESSearchClient()
    client._initialized = True
    client._available = True
    client._client = AsyncMock()

    result = await client.delete_product("product-id")

    assert result is True
    client._client.delete.assert_awaited_once_with(
        index=client._index_products,
        id="product-id",
        refresh="wait_for",
    )
