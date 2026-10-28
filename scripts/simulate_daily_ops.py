#!/usr/bin/env python3
"""Simulate overnight daily catalog refresh (刷数) ops end-to-end."""
from __future__ import annotations

import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
import argparse
from pathlib import Path

from scripts._common import ROOT, get_app, jlog


def banner(step: int, title: str) -> None:
    print()
    print("=" * 60)
    print(f"[{step}] {title}")
    print("=" * 60)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Simulate daily mall ops refresh")
    parser.add_argument("--csv", default=str(ROOT / "data" / "catalog_upstream.csv"))
    parser.add_argument("--baseline", default=str(ROOT / "data" / "stock_baseline.csv"))
    args = parser.parse_args(argv)

    jlog("daily_ops_start", scenario="overnight_catalog_sync")

    banner(1, "Receive upstream catalog CSV (nightly file drop)")
    csv_path = Path(args.csv)
    print(f"  feed: {csv_path}")
    print(f"  exists: {csv_path.exists()}")
    jlog("feed_ready", path=str(csv_path), exists=csv_path.exists())

    banner(2, "Refresh: upsert categories/products + soft-delete stale SKUs")
    from scripts.refresh_catalog import refresh

    app = get_app()
    with app.app_context():
        summary = refresh(csv_path, soft_delete=True)
        print(f"  categories_touched={summary['categories_touched']}")
        print(f"  products_upserted={summary['products_upserted']}")
        print(f"  soft_deleted={summary['soft_deleted']}")

        banner(3, "Invalidate Redis catalog cache (called inside refresh)")
        print("  invalidate_catalog_cache() done (or degraded if Redis down)")

        banner(4, "Reconcile: order deductions vs stock vs baseline")
        from scripts.reconcile_stock import reconcile

        result = reconcile(Path(args.baseline))
        s = result["summary"]
        print(f"  checked={s['checked']} ok={s['ok']} anomalies={s['anomalies']}")
        for a in result["anomalies"][:10]:
            print(
                f"  ! {a.get('slug')}: flags={a.get('flags')} "
                f"stock={a.get('stock')} sold={a.get('sold')} drift={a.get('drift')}"
            )

        banner(5, "On-call checklist")
        print("  - Review anomaly JSON lines; confirm drift (returns / offline moves)")
        print("  - Soft-deleted SKUs hidden on /shop; still visible in admin")
        print("  - Spot-check /shop and /admin/products")
        print("  - Rollback: re-run refresh_catalog.py with yesterday CSV")

    jlog("daily_ops_done", status="ok")
    print()
    print("Daily ops simulation finished. See docs/ops-daily-refresh.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
