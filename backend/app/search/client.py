"""Elasticsearch 异步搜索客户端。

用途: 商品全文搜索、分类筛选、价格区间过滤、关键词高亮。

Author: SnapTrip Team
Date: 2026-05-26
"""

from __future__ import annotations

from typing import Any

from snaptrip_shared.core.logging import get_logger

from app.core.config import commerce_settings

logger = get_logger(__name__)


class ESSearchClient:
    """Elasticsearch 异步客户端 —— 封装常用搜索操作"""

    def __init__(self) -> None:
        self._client: Any = None
        self._hosts = commerce_settings.es_hosts_list
        self._username = commerce_settings.ES_USERNAME
        self._password = commerce_settings.ES_PASSWORD
        self._index_products = commerce_settings.ES_INDEX_PRODUCTS
        self._timeout = commerce_settings.ES_SEARCH_TIMEOUT
        self._initialized = False

    async def _ensure_client(self) -> None:
        """懒初始化 ES 客户端"""
        if self._initialized:
            return
        try:
            from elasticsearch import AsyncElasticsearch

            kwargs: dict[str, Any] = {
                "hosts": self._hosts,
                "request_timeout": self._timeout,
            }
            if self._username and self._password:
                kwargs["basic_auth"] = (self._username, self._password)

            self._client = AsyncElasticsearch(**kwargs)
            logger.info("es_client_connected", hosts=self._hosts)
        except ImportError:
            logger.warning("es_import_failed", fallback="db_search")
            raise RuntimeError(
                "elasticsearch 未安装。安装命令: pip install elasticsearch[async]"
            ) from None
        self._initialized = True

    async def close(self) -> None:
        if self._client is not None:
            await self._client.close()
            self._initialized = False

    async def health_check(self) -> bool:
        """ES 集群健康检查"""
        try:
            await self._ensure_client()
            assert self._client is not None
            info = await self._client.cluster.health()
            return info.get("status") in ("green", "yellow")
        except Exception as exc:
            logger.warning("es_health_check_failed", error=str(exc))
            return False

    async def index_product(self, product_id: str, doc: dict[str, Any]) -> bool:
        """索引单个商品文档"""
        try:
            await self._ensure_client()
            assert self._client is not None
            await self._client.index(
                index=self._index_products,
                id=product_id,
                document=doc,
            )
            logger.info("es_product_indexed", product_id=product_id)
            return True
        except Exception as exc:
            logger.error("es_index_failed", product_id=product_id, error=str(exc))
            return False

    async def bulk_index_products(self, docs: list[dict[str, Any]]) -> int:
        """批量索引商品, 返回成功数"""
        try:
            await self._ensure_client()
            assert self._client is not None
            from elasticsearch.helpers import async_bulk

            actions = [
                {
                    "_index": self._index_products,
                    "_id": doc["id"],
                    "_source": doc,
                }
                for doc in docs
            ]
            success, errors = await async_bulk(self._client, actions, raise_on_error=False)
            logger.info("es_bulk_indexed", success=success, errors=len(errors))
            return success  # type: ignore[no-any-return]
        except Exception as exc:
            logger.error("es_bulk_index_failed", error=str(exc))
            return 0

    async def delete_product(self, product_id: str) -> bool:
        """从索引中删除商品"""
        try:
            await self._ensure_client()
            assert self._client is not None
            await self._client.delete(index=self._index_products, id=product_id)
            logger.info("es_product_deleted", product_id=product_id)
            return True
        except Exception as exc:
            logger.warning("es_delete_failed", product_id=product_id, error=str(exc))
            return False

    async def search_products(
        self,
        keyword: str = "",
        category_id: str | None = None,
        brand_id: str | None = None,
        min_price: float | None = None,
        max_price: float | None = None,
        sort_by: str = "default",
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        """商品全文搜索 —— 多条件组合 + 排序"""
        try:
            await self._ensure_client()
            assert self._client is not None

            must_clauses: list[dict[str, Any]] = []
            filter_clauses: list[dict[str, Any]] = []

            if keyword:
                must_clauses.append({
                    "multi_match": {
                        "query": keyword,
                        "fields": ["name^3", "sub_title^2", "keywords", "brand_name"],
                        "type": "best_fields",
                    }
                })

            if category_id:
                filter_clauses.append({"term": {"category_id": category_id}})
            if brand_id:
                filter_clauses.append({"term": {"brand_id": brand_id}})
            if min_price is not None or max_price is not None:
                price_range: dict[str, Any] = {"price": {}}
                if min_price is not None:
                    price_range["price"]["gte"] = min_price
                if max_price is not None:
                    price_range["price"]["lte"] = max_price
                filter_clauses.append({"range": price_range})

            sort_configs: list[dict[str, Any]] = []
            if sort_by == "price_asc":
                sort_configs.append({"price": {"order": "asc"}})
            elif sort_by == "price_desc":
                sort_configs.append({"price": {"order": "desc"}})
            elif sort_by == "sales":
                sort_configs.append({"sale_count": {"order": "desc"}})
            elif sort_by == "new":
                sort_configs.append({"publish_time": {"order": "desc"}})

            if not sort_configs:
                sort_configs.append({"_score": {"order": "desc"}})

            body: dict[str, Any] = {
                "from": (page - 1) * page_size,
                "size": page_size,
                "query": {
                    "bool": {
                        "must": must_clauses,
                        "filter": filter_clauses,
                    }
                },
                "sort": sort_configs,
                "highlight": {
                    "fields": {"name": {}, "sub_title": {}}
                },
            }

            result = await self._client.search(
                index=self._index_products,
                body=body,
            )

            hits = result["hits"]
            return {
                "items": [
                    {
                        "id": hit["_id"],
                        "score": hit["_score"],
                        "highlight": hit.get("highlight", {}),
                        **hit["_source"],
                    }
                    for hit in hits["hits"]
                ],
                "total": hits["total"]["value"],
                "page": page,
                "page_size": page_size,
            }
        except Exception as exc:
            logger.error("es_search_failed", keyword=keyword, error=str(exc))
            return {"items": [], "total": 0, "page": page, "page_size": page_size}

    async def create_product_index(self) -> bool:
        """创建商品搜索索引 —— 仅首次部署使用"""
        try:
            await self._ensure_client()
            assert self._client is not None

            exists = await self._client.indices.exists(index=self._index_products)
            if exists:
                logger.info("es_index_exists", index=self._index_products)
                return True

            mapping = {
                "settings": {
                    "number_of_shards": 1,
                    "number_of_replicas": 0,
                    "analysis": {
                        "analyzer": {
                            "ik_smart_analyzer": {
                                "type": "custom",
                                "tokenizer": "ik_smart",
                            }
                        }
                    },
                },
                "mappings": {
                    "properties": {
                        "id": {"type": "keyword"},
                        "name": {
                            "type": "text",
                            "analyzer": "ik_smart_analyzer",
                            "fields": {"keyword": {"type": "keyword"}},
                        },
                        "sub_title": {"type": "text", "analyzer": "ik_smart_analyzer"},
                        "keywords": {"type": "text", "analyzer": "ik_smart_analyzer"},
                        "category_id": {"type": "keyword"},
                        "category_name": {"type": "keyword"},
                        "brand_id": {"type": "keyword"},
                        "brand_name": {"type": "text"},
                        "price": {"type": "float"},
                        "promotion_price": {"type": "float"},
                        "sale_count": {"type": "integer"},
                        "stock": {"type": "integer"},
                        "pics": {"type": "keyword"},
                        "publish_status": {"type": "integer"},
                        "verify_status": {"type": "integer"},
                        "publish_time": {"type": "date"},
                    }
                },
            }

            await self._client.indices.create(index=self._index_products, body=mapping)
            logger.info("es_index_created", index=self._index_products)
            return True
        except Exception as exc:
            logger.error("es_create_index_failed", error=str(exc))
            return False


# ── 全局搜索客户端单例 ──

_search_client: ESSearchClient | None = None


def get_search_client() -> ESSearchClient:
    """获取 ES 搜索客户端单例"""
    global _search_client
    if _search_client is None:
        _search_client = ESSearchClient()
    return _search_client


async def close_search_client() -> None:
    """关闭 ES 连接"""
    global _search_client
    if _search_client is not None:
        await _search_client.close()
        _search_client = None
