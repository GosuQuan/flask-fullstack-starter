#!/usr/bin/env python3
"""Reconcile product stock vs order deductions; report anomalies as JSON lines."""
from __future__ import annotations

import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
import argparse
import csv
from pathlib import Path

from scripts._common import ROOT, get_app, jlog


def load_baseline(path: Path) -> dict[str, int]:
    if not path.exists():
        return {}
    out = {}
    with path.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            slug = (row.get("product_slug") or "").strip()
            if slug:
                out[slug] = int(row.get("baseline_stock") or 0)
    return out


def reconcile(baseline_path: Path | None = None) -> dict:
    from sqlalchemy import func

    from app.models import Order, OrderItem, Product

    baseline = load_baseline(baseline_path) if baseline_path else {}
    jlog("reconcile_start", baseline_skus=len(baseline))

    sold_rows = (
        OrderItem.query.join(Order, OrderItem.order_id == Order.id)
        .filter(Order.status != "cancelled")
        .with_entities(OrderItem.product_id, func.coalesce(func.sum(OrderItem.quantity), 0))
        .group_by(OrderItem.product_id)
        .all()
    )
    sold_by_pid = {pid: int(qty) for pid, qty in sold_rows if pid is not None}

    anomalies = []
    ok = 0
    for prod in Product.query.order_by(Product.id).all():
        sold = sold_by_pid.get(prod.id, 0)
        entry = {
            "slug": prod.slug,
            "stock": prod.stock,
            "sold": sold,
            "is_active": prod.is_active,
        }
        flags = []
        if prod.stock < 0:
            flags.append("negative_stock")
        if prod.slug in baseline:
            expected = baseline[prod.slug] - sold
            entry["baseline"] = baseline[prod.slug]
            entry["expected_stock"] = expected
            drift = prod.stock - expected
            entry["drift"] = drift
            if abs(drift) > 0:
                flags.append("drift_vs_baseline")
        if (not prod.is_active) and prod.stock > 0:
            flags.append("inactive_with_stock")
        if flags:
            entry["flags"] = flags
            anomalies.append(entry)
            jlog("stock_anomaly", **entry)
        else:
            ok += 1
            jlog("stock_ok", **entry)

    summary = {"ok": ok, "anomalies": len(anomalies), "checked": ok + len(anomalies)}
    jlog("reconcile_done", **summary)
    return {"summary": summary, "anomalies": anomalies}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Reconcile stock vs orders")
    parser.add_argument("--baseline", default=str(ROOT / "data" / "stock_baseline.csv"))
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args(argv)
    app = get_app()
    with app.app_context():
        result = reconcile(Path(args.baseline) if args.baseline else None)
    if args.strict and result["summary"]["anomalies"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
