"""
site_adapter.py — Integration layer with main y-store.in.ua backend.

ЦЕ СКЕЛЕТ. Дев-розробник має:
1. Заповнити SITE_API_URL / SITE_API_TOKEN у .env
2. Реалізувати _normalize_product / _normalize_category / _map_order
   під реальну схему відповідей вашого REST API (або SQL, через SQLAlchemy).
3. Увімкнути SITE_ADAPTER_ENABLED=1 у .env
4. У modules/tma/routes.py замінити прямі db.* виклики на
   site_adapter.list_products(...) і т.д. (див. INTEGRATION_AUDIT.md §5.3)

Файл безпечний: поки SITE_ADAPTER_ENABLED!=1, він нікуди не ходить.
"""
from __future__ import annotations

import logging
import os
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)


SITE_API_URL = os.getenv("SITE_API_URL", "").rstrip("/")
SITE_API_TOKEN = os.getenv("SITE_API_TOKEN", "")
SITE_ADAPTER_ENABLED = os.getenv("SITE_ADAPTER_ENABLED", "0") == "1"


class SiteAdapterError(Exception):
    """Помилка виклику API сайту."""


class SiteAdapter:
    """
    Тонкий HTTP-клієнт до backend y-store.in.ua.
    Ленивий httpx.AsyncClient — створюється при першому виклику.
    """

    def __init__(self) -> None:
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def enabled(self) -> bool:
        return SITE_ADAPTER_ENABLED and bool(SITE_API_URL)

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            headers: dict[str, str] = {"Accept": "application/json"}
            if SITE_API_TOKEN:
                headers["Authorization"] = f"Bearer {SITE_API_TOKEN}"
            self._client = httpx.AsyncClient(
                base_url=SITE_API_URL,
                headers=headers,
                timeout=httpx.Timeout(15.0, connect=5.0),
            )
        return self._client

    async def aclose(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    # ======================= Products =======================

    async def list_products(self, filters: dict[str, Any]) -> dict[str, Any]:
        """
        filters = {
            'q': str,                     # пошук по title/brand/description
            'category_slug': str,
            'limit': int, 'skip': int,
            'sort': 'featured|price_asc|price_desc|new',
        }
        → [TMAProductOut]
        """
        if not self.enabled:
            raise SiteAdapterError("site_adapter not enabled")

        q = filters.get("q") or ""
        category_slug = filters.get("category_slug") or ""
        limit = int(filters.get("limit") or 20)
        skip = int(filters.get("skip") or 0)
        sort = filters.get("sort") or "featured"
        page = max(1, (skip // max(limit, 1)) + 1)

        # First try catalog-v2 endpoint that supports category slugs directly.
        candidates: list[tuple[str, dict[str, Any]]] = [
            (
                "/api/v2/catalog",
                {
                    "category": category_slug or None,
                    "sort_by": self._map_sort(sort),
                    "page": page,
                    "limit": limit,
                },
            ),
            (
                "/api/v1/products",
                {
                    "q": q or None,
                    "category": category_slug or None,
                    "limit": limit,
                    "offset": skip,
                    "sort": sort,
                },
            ),
        ]

        if q:
            candidates.insert(
                0,
                (
                    "/api/products",
                    {
                        "search": q,
                        "sort_by": self._map_sort(sort),
                        "sort_order": "asc" if sort == "price_asc" else "desc",
                        "page": page,
                        "limit": limit,
                    },
                ),
            )

        cat_id = None
        if category_slug:
            cat_id = await self._resolve_category_id_by_slug(category_slug)
            if cat_id:
                candidates.insert(
                    0,
                    (
                        "/api/products",
                        {
                            "category_id": cat_id,
                            "search": q or None,
                            "sort_by": self._map_sort(sort),
                            "sort_order": "asc" if sort == "price_asc" else "desc",
                            "page": page,
                            "limit": limit,
                        },
                    ),
                )

        last_err: Optional[Exception] = None
        for path, raw_params in candidates:
            params = {k: v for k, v in raw_params.items()
                      if v not in (None, "")}
            try:
                r = await self.client.get(path, params=params)
                if r.status_code == 404:
                    continue
                r.raise_for_status()
                data = r.json()
                raw_items = data.get("items") or data.get(
                    "products") or data.get("data") or []
                items = [self._normalize_product(p) for p in raw_items]
                total = int(data.get("total") or len(items))
                return {"items": items, "total": total}
            except httpx.HTTPError as e:
                last_err = e

        raise SiteAdapterError(
            f"Cannot list products via site API: {last_err}")

    async def get_product(self, product_id: str) -> Optional[dict]:
        """Один товар + related."""
        if not self.enabled:
            raise SiteAdapterError("site_adapter not enabled")

        prod = None
        prod_err: Optional[Exception] = None
        for path in (
            f"/api/products/{product_id}",
            f"/api/v1/products/{product_id}",
        ):
            try:
                r = await self.client.get(path)
                if r.status_code == 404:
                    continue
                r.raise_for_status()
                prod = self._normalize_product(r.json())
                break
            except httpx.HTTPError as e:
                prod_err = e

        if prod is None:
            if prod_err:
                raise SiteAdapterError(
                    f"Cannot fetch product {product_id}: {prod_err}")
            return None

        # related
        related: list[dict] = []
        try:
            rr = await self.client.get(f"/api/v1/products/{product_id}/related", params={"limit": 6})
            if rr.status_code == 200:
                raw_related = rr.json().get("items") or rr.json().get("products") or []
                related = [self._normalize_product(p) for p in raw_related]
        except httpx.HTTPError as e:
            # Fallback for stores without a dedicated related endpoint.
            try:
                category_id = prod.get("category_id")
                if category_id:
                    lr = await self.client.get(
                        "/api/products",
                        params={"category_id": category_id,
                                "page": 1, "limit": 8},
                    )
                    if lr.status_code == 200:
                        raw_related = lr.json().get("items") or lr.json().get("products") or []
                        normalized = [self._normalize_product(
                            p) for p in raw_related]
                        related = [p for p in normalized if p.get(
                            "id") != str(product_id)][:6]
            except httpx.HTTPError as ie:
                logger.warning(
                    f"site_adapter.get_product related fallback failed: {ie}")
            logger.warning(f"site_adapter.get_product related failed: {e}")
        prod["related"] = related
        return prod

    # ======================= Categories =======================

    async def list_categories(self) -> list[dict]:
        """→ [TMACategoryOut]"""
        if not self.enabled:
            raise SiteAdapterError("site_adapter not enabled")

        last_err: Optional[Exception] = None
        for path in ("/api/categories", "/api/v1/categories", "/api/v2/categories/tree"):
            try:
                r = await self.client.get(path)
                if r.status_code == 404:
                    continue
                r.raise_for_status()
                data = r.json()
                raw_items = data.get("items") or data.get(
                    "categories") or data.get("data") or []
                if path.endswith("/tree"):
                    raw_items = self._flatten_tree(raw_items)
                return [self._normalize_category(c) for c in raw_items]
            except httpx.HTTPError as e:
                last_err = e

        raise SiteAdapterError(
            f"Cannot list categories via site API: {last_err}")

    # ======================= Orders =======================

    async def register_order(self, tma_order: dict) -> dict:
        """
        Ідемпотентно (upsert за external_id=order_number) імпортує TMA-замовлення
        у головну CRM. Викликається:
          1. після POST /api/tma/orders (щойно створено)
          2. після WayForPay webhook (після зміни статусу)
          3. після створення ТТН (щоб сайт знав tracking_number)

        → {"ok": True, "site_order_id": str, "crm_url": str|None}
        """
        if not self.enabled:
            raise SiteAdapterError("site_adapter not enabled")

        payload = self._map_order(tma_order)
        last_err: Optional[Exception] = None

        for path, body in (
            ("/api/v1/orders/import", payload),
            ("/api/orders/import", payload),
            ("/api/orders", self._map_order_for_orders_endpoint(tma_order)),
        ):
            try:
                r = await self.client.post(path, json=body)
                if r.status_code in (401, 403, 404):
                    continue
                r.raise_for_status()
                data = r.json() if "application/json" in r.headers.get("content-type", "") else {}
                return {
                    "ok": True,
                    "site_order_id": str(data.get("id") or data.get("order_id") or ""),
                    "crm_url": data.get("admin_url") or data.get("crm_url"),
                }
            except httpx.HTTPError as e:
                last_err = e

        raise SiteAdapterError(
            f"Cannot register order in site backend: {last_err}")

    # ======================= Users =======================

    async def match_user(
        self,
        telegram_id: int,
        telegram_username: Optional[str] = None,
        phone: Optional[str] = None,
    ) -> Optional[dict]:
        """
        Спробувати знайти користувача сайту по telegram_id або phone.
        Повертає {'site_user_id', 'email', 'bonus_points', 'saved_addresses', ...}
        або None якщо не знайдено / не підтримується.
        """
        if not self.enabled:
            return None

        payload = {
            "telegram_id": telegram_id,
            "telegram_username": telegram_username,
            "phone": phone,
        }

        for method, path in (
            ("post", "/api/v1/users/match"),
            ("post", "/api/users/match"),
            ("get", "/api/customers/by-phone"),
        ):
            try:
                if method == "post":
                    r = await self.client.post(path, json=payload)
                else:
                    if not phone:
                        continue
                    r = await self.client.get(path, params={"phone": phone})

                if r.status_code != 200:
                    continue
                data = r.json()
                if data:
                    return data
            except httpx.HTTPError as e:
                logger.warning(
                    f"site_adapter.match_user failed via {path}: {e}")
        return None

    def _map_sort(self, sort: str) -> str:
        mapping = {
            "featured": "popular",
            "new": "new",
            "price_asc": "price_asc",
            "price_desc": "price_desc",
        }
        return mapping.get(sort, "popular")

    async def _resolve_category_id_by_slug(self, slug: str) -> Optional[str]:
        try:
            cats = await self.list_categories()
            for c in cats:
                if c.get("slug") == slug:
                    return str(c.get("id") or "")
        except Exception:
            return None
        return None

    def _flatten_tree(self, items: list[dict]) -> list[dict]:
        flat: list[dict] = []
        stack = list(items)
        while stack:
            node = stack.pop(0)
            flat.append({k: v for k, v in node.items() if k != "children"})
            children = node.get("children") or []
            if children:
                stack.extend(children)
        return flat

    # ======================= Normalizers =======================
    # ⚠️ ЦЕ СКЕЛЕТИ. Дев заповнить під реальну схему відповідей сайту.

    def _normalize_product(self, p: dict) -> dict:
        """Z→TMAProductOut (див. core/models + modules/tma/routes.product_to_out)."""
        return {
            "id": str(p.get("id") or p.get("product_id") or p.get("slug") or ""),
            "title": p.get("title") or p.get("name") or "Товар",
            "slug": p.get("slug"),
            "brand": p.get("brand") or (p.get("manufacturer") or {}).get("name"),
            "category_id": str(p.get("category_id") or (p.get("category") or {}).get("id") or ""),
            "category_slug": (p.get("category") or {}).get("slug") or p.get("category_slug"),
            "description": p.get("description", "") or p.get("short_description", ""),
            "price": float(p.get("price") or 0),
            "old_price": float(p["old_price"]) if p.get("old_price") else (
                float(p["compare_price"]) if p.get("compare_price") else None
            ),
            "images": p.get("gallery") or p.get("images") or [],
            "in_stock": bool(p.get("in_stock", p.get("available", True))),
            "is_bestseller": bool(p.get("is_bestseller", False)),
            "rating": float(p.get("rating") or p.get("avg_rating") or 0),
            "reviews_count": int(p.get("reviews_count") or 0),
            "specifications": p.get("specifications") or p.get("specs") or p.get("attributes") or {},
        }

    def _normalize_category(self, c: dict) -> dict:
        """Z→TMACategoryOut."""
        return {
            "id": str(c.get("id") or c.get("slug") or ""),
            "slug": c["slug"],
            "name": c.get("name") or c.get("title") or c["slug"],
            "name_uk": c.get("name_uk") or c.get("name"),
            "icon": c.get("icon"),
            "image": c.get("image") or c.get("cover_url"),
            "product_count": int(c.get("products_count") or c.get("product_count") or 0),
        }

    def _map_order(self, o: dict) -> dict:
        """TMA order → CRM import payload. АДАПТУВАТИ під реальну CRM-схему сайту."""
        customer = o.get("customer") or {}
        delivery = o.get("delivery") or {}
        return {
            "external_id": o["order_number"],
            "source": "telegram_mini_app",
            "customer": {
                "full_name": customer.get("full_name"),
                "first_name": customer.get("first_name"),
                "last_name": customer.get("last_name"),
                "phone": customer.get("phone"),
                "email": customer.get("email"),
                "telegram_id": customer.get("telegram_id"),
                "telegram_username": customer.get("telegram_username"),
            },
            "line_items": [
                {
                    "product_id": it.get("product_id"),
                    "sku": it.get("product_id"),
                    "title": it.get("title"),
                    "qty": it.get("quantity"),
                    "unit_price": it.get("price"),
                }
                for it in (o.get("items") or [])
            ],
            "delivery": {
                "method": delivery.get("method"),
                "city_name": delivery.get("city_name"),
                "city_ref": delivery.get("city_ref"),
                "warehouse_name": delivery.get("warehouse_name"),
                "warehouse_ref": delivery.get("warehouse_ref"),
                "delivery_cost": delivery.get("delivery_cost"),
                "tracking_number": delivery.get("tracking_number"),
                "tracking_provider": delivery.get("tracking_provider"),
                "estimated_delivery_date": delivery.get("estimated_delivery_date"),
            },
            "totals": {
                "subtotal": o.get("subtotal"),
                "shipping": o.get("shipping_cost"),
                "total": o.get("total_amount"),
                "currency": o.get("currency", "UAH"),
            },
            "status": o.get("status"),
            "payment_status": o.get("payment_status"),
            "payment_method": o.get("payment_method"),
            "payment": o.get("payment"),
            "comment": o.get("comment"),
            "metadata": {
                "order_number": o["order_number"],
                "telegram_id": customer.get("telegram_id"),
                "telegram_username": customer.get("telegram_username"),
                "tma_user_id": o.get("buyer_id"),
            },
            "created_at": o.get("created_at"),
            "updated_at": o.get("updated_at"),
        }

    def _map_order_for_orders_endpoint(self, o: dict) -> dict:
        customer = o.get("customer") or {}
        delivery = o.get("delivery") or {}
        return {
            "shipping": {
                "full_name": customer.get("full_name") or "",
                "phone": customer.get("phone") or "",
                "city": delivery.get("city_name") or "",
                "address": delivery.get("warehouse_name") or "",
                "np_department": delivery.get("warehouse_name") or "",
                "notes": o.get("comment") or "",
            },
            "payment_method": "cash" if o.get("payment_method") in ("cash", "cash_on_delivery") else "card",
            "notes": f"Imported from TMA order {o.get('order_number')}",
        }


site_adapter = SiteAdapter()
