#!/usr/bin/env python3
"""Upsert categories/products from an upstream CSV feed; soft-delete missing SKUs."""
from __future__ import annotations

import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
import argparse
import csv
from decimal import Decimal
from pathlib import Path

from scripts._common import ROOT, get_app, jlog


def load_rows(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def refresh(csv_path: Path, soft_delete: bool = True) -> dict:
    from app.extensions import db
    from app.models import Category, Product
    from app.services.audit import log_action
    from app.services.catalog import invalidate_catalog_cache

    rows = load_rows(csv_path)
    jlog("refresh_start", source=str(csv_path), rows=len(rows))

    seen_product_slugs: set[str] = set()
    cats_upserted = prods_upserted = 0

    for row in rows:
        cslug = (row.get("category_slug") or "").strip()
        if not cslug:
            continue
        cat = Category.query.filter_by(slug=cslug).first()
        cname = (row.get("category_name") or cslug).strip()
        sort_order = int(row.get("sort_order") or 0)
        if cat is None:
            cat = Category(slug=cslug, name=cname, sort_order=sort_order)
            db.session.add(cat)
            db.session.flush()
            jlog("category_created", slug=cslug)
        else:
            cat.name = cname
            cat.sort_order = sort_order
        cats_upserted += 1

        pslug = (row.get("product_slug") or "").strip()
        if not pslug:
            continue
        active_flag = str(row.get("is_active", "1")).strip() in ("1", "true", "True", "yes")
        seen_product_slugs.add(pslug)

        prod = Product.query.filter_by(slug=pslug).first()
        price = Decimal(str(row.get("price") or "0"))
        stock = int(row.get("stock") or 0)
        name = (row.get("product_name") or pslug).strip()
        desc = row.get("description") or ""
        if prod is None:
            prod = Product(
                category_id=cat.id,
                slug=pslug,
                name=name,
                description=desc,
                price=price,
                stock=stock,
                is_active=active_flag,
            )
            db.session.add(prod)
            jlog("product_created", slug=pslug, stock=stock, is_active=active_flag)
        else:
            prod.category_id = cat.id
            prod.name = name
            prod.description = desc
            prod.price = price
            prod.stock = stock
            prod.is_active = active_flag
            jlog("product_updated", slug=pslug, stock=stock, is_active=active_flag)
        prods_upserted += 1

    soft_deleted = 0
    if soft_delete:
        for prod in Product.query.filter_by(is_active=True).all():
            if prod.slug not in seen_product_slugs:
                prod.is_active = False
                soft_deleted += 1
                jlog("product_soft_deleted", slug=prod.slug, reason="missing_from_upstream")

    db.session.commit()
    try:
        invalidate_catalog_cache()
    except Exception as exc:  # noqa: BLE001
        jlog("cache_invalidate_warn", error=str(exc))
    try:
        log_action(None, "catalog.refresh", "catalog", None, f"rows={len(rows)} soft_deleted={soft_deleted}")
    except Exception:
        pass

    summary = {
        "categories_touched": cats_upserted,
        "products_upserted": prods_upserted,
        "soft_deleted": soft_deleted,
        "feed_skus": len(seen_product_slugs),
    }
    jlog("refresh_done", **summary)
    return summary


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Daily catalog refresh from CSV")
    parser.add_argument("--csv", default=str(ROOT / "data" / "catalog_upstream.csv"))
    parser.add_argument("--no-soft-delete", action="store_true")
    args = parser.parse_args(argv)
    app = get_app()
    with app.app_context():
        refresh(Path(args.csv), soft_delete=not args.no_soft_delete)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
