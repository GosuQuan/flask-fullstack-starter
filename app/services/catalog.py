"""Category / product catalog service + Redis cache."""
from __future__ import annotations

import json
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import joinedload, load_only

from app.extensions import db
from app.models import Category, Product
from app.services import redis_client
from app.services.audit import log_action
from app.utils_slug import slugify

PRODUCT_TTL = 30
LIST_TTL = 20


def _product_to_dict(p: Product) -> dict:
    return {
        "id": p.id,
        "name": p.name,
        "slug": p.slug,
        "description": p.description or "",
        "price": str(p.price),
        "stock": p.stock,
        "is_active": bool(p.is_active),
        "cover_url": p.cover_url,
        "category_id": p.category_id,
        "category_slug": p.category.slug if p.category else None,
        "category_name": p.category.name if p.category else None,
    }


def invalidate_catalog_cache() -> None:
    redis_client.cache_delete_pattern("mall:product:*")
    redis_client.cache_delete_pattern("mall:products:*")
    redis_client.cache_delete("mall:categories:all")


def list_categories():
    key = "mall:categories:all"
    cached = redis_client.cache_get(key)
    if cached:
        return json.loads(cached), "HIT"
    rows = db.session.scalars(
        select(Category).order_by(Category.sort_order.asc(), Category.id.asc())
    ).all()
    data = [
        {"id": c.id, "name": c.name, "slug": c.slug, "sort_order": c.sort_order}
        for c in rows
    ]
    redis_client.cache_set(key, json.dumps(data, ensure_ascii=False), LIST_TTL)
    return data, "MISS"


def get_product_by_slug(slug: str):
    key = f"mall:product:{slug}"
    cached = redis_client.cache_get(key)
    if cached:
        return json.loads(cached), "HIT"
    p = db.session.scalars(
        select(Product)
        .options(joinedload(Product.category))
        .where(Product.slug == slug, Product.is_active.is_(True))
    ).first()
    if not p:
        return None, "MISS"
    data = _product_to_dict(p)
    redis_client.cache_set(key, json.dumps(data, ensure_ascii=False), PRODUCT_TTL)
    return data, "MISS"


def list_products(category_slug=None, page=1, page_size=12, active_only=True):
    key = f"mall:products:{category_slug or 'all'}:{page}:{page_size}:{int(active_only)}"
    cached = redis_client.cache_get(key)
    if cached:
        return json.loads(cached), "HIT"

    stmt = select(Product).options(
        load_only(
            Product.id,
            Product.name,
            Product.slug,
            Product.price,
            Product.stock,
            Product.is_active,
            Product.cover_url,
            Product.category_id,
            Product.created_at,
        ),
        joinedload(Product.category).load_only(Category.id, Category.name, Category.slug),
    )
    if active_only:
        stmt = stmt.where(Product.is_active.is_(True))
    if category_slug:
        stmt = stmt.join(Category).where(Category.slug == category_slug)

    from sqlalchemy import func

    count_stmt = select(func.count()).select_from(Product)
    if active_only:
        count_stmt = count_stmt.where(Product.is_active.is_(True))
    if category_slug:
        count_stmt = count_stmt.join(Category).where(Category.slug == category_slug)

    total = db.session.scalar(count_stmt) or 0
    pages = max(1, (total + page_size - 1) // page_size)
    page = min(max(1, page), pages)
    rows = db.session.scalars(
        stmt.order_by(Product.id.desc()).offset((page - 1) * page_size).limit(page_size)
    ).unique().all()
    items = [_product_to_dict(p) for p in rows]
    payload = {"items": items, "total": total, "page": page, "pages": pages}
    redis_client.cache_set(key, json.dumps(payload, ensure_ascii=False), LIST_TTL)
    return payload, "MISS"


def create_category(name: str, slug: str | None = None, sort_order: int = 0) -> Category:
    slug = slugify(slug or name, fallback="cat")
    c = Category(name=name.strip(), slug=slug, sort_order=sort_order)
    db.session.add(c)
    log_action("category.create", "category", detail=slug)
    db.session.commit()
    invalidate_catalog_cache()
    return c


def update_category(cat: Category, name: str, slug: str, sort_order: int) -> Category:
    cat.name = name.strip()
    cat.slug = slugify(slug or name)
    cat.sort_order = sort_order
    log_action("category.update", "category", cat.id, cat.slug)
    db.session.commit()
    invalidate_catalog_cache()
    return cat


def delete_category(cat: Category) -> None:
    cid, slug = cat.id, cat.slug
    db.session.delete(cat)
    log_action("category.delete", "category", cid, slug)
    db.session.commit()
    invalidate_catalog_cache()


def create_product(**kwargs) -> Product:
    slug = slugify(kwargs.get("slug") or kwargs["name"], fallback="product")
    p = Product(
        category_id=kwargs["category_id"],
        name=kwargs["name"].strip(),
        slug=slug,
        description=kwargs.get("description") or "",
        price=Decimal(str(kwargs.get("price") or 0)),
        stock=int(kwargs.get("stock") or 0),
        is_active=bool(kwargs.get("is_active", True)),
        cover_url=kwargs.get("cover_url") or None,
    )
    db.session.add(p)
    log_action("product.create", "product", detail=slug)
    db.session.commit()
    invalidate_catalog_cache()
    return p


def update_product(p: Product, **kwargs) -> Product:
    p.category_id = kwargs["category_id"]
    p.name = kwargs["name"].strip()
    p.slug = slugify(kwargs.get("slug") or p.name)
    p.description = kwargs.get("description") or ""
    p.price = Decimal(str(kwargs.get("price") or 0))
    p.stock = int(kwargs.get("stock") or 0)
    p.is_active = bool(kwargs.get("is_active", True))
    p.cover_url = kwargs.get("cover_url") or None
    log_action("product.update", "product", p.id, p.slug)
    db.session.commit()
    invalidate_catalog_cache()
    return p


def delete_product(p: Product) -> None:
    pid, slug = p.id, p.slug
    db.session.delete(p)
    log_action("product.delete", "product", pid, slug)
    db.session.commit()
    invalidate_catalog_cache()
