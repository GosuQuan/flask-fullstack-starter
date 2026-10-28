# Daily 刷数 (catalog refresh) simulation

## Scenario (overnight batch)

1. Upstream drops a catalog CSV (prices, stock, active flags).
2. Job upserts categories/products by `slug`.
3. SKUs missing from today's feed are **soft-deleted** (`is_active=false`).
4. Redis catalog cache is invalidated.
5. Stock is reconciled against non-cancelled order lines + optional baseline CSV; drift is flagged for humans.

## Sample data

- `data/catalog_upstream.csv` — nightly feed
- `data/stock_baseline.csv` — expected stock before sales (for drift)

## Commands

```powershell
cd "C:\Users\admin\Desktop\05-项目\flask-fullstack-starter"
.\.venv\Scripts\Activate.ps1

# Full demo narrative
python scripts/simulate_daily_ops.py

# Pieces
python scripts/refresh_catalog.py --csv data/catalog_upstream.csv
python scripts/reconcile_stock.py --baseline data/stock_baseline.csv
```

Requires local Postgres (`flask-starter-pg`). Redis optional (cache invalidate degrades).

## Exit / ops meaning

- `stock_anomaly` with `drift_vs_baseline`: sold + remaining ≠ baseline → check returns/manual adjusts.
- `product_soft_deleted`: SKU left the feed → hidden on storefront.
- Re-run yesterday's CSV to roll back catalog fields.
