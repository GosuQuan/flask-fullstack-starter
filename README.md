[![CI](https://github.com/GosuQuan/flask-fullstack-starter/actions/workflows/ci.yml/badge.svg)](https://github.com/GosuQuan/flask-fullstack-starter/actions/workflows/ci.yml)

# Flask Mall Starter

可用演示商城：**前台购物 + 后台类目/商品/订单/用户**，PostgreSQL + Redis + Flask-Login。

## 快速开始

```powershell
cd "C:\Users\admin\Desktop\05-项目\flask-fullstack-starter"
# 需 Postgres(flask-starter-pg) + Redis(flask-starter-redis)
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python run.py
```

- 商城：http://127.0.0.1:5000/shop
- 后台：http://127.0.0.1:5000/admin/ （`admin` / `admin123`，仅本地 demo）

## 文档
- [`docs/mall.md`](docs/mall.md)
- [`docs/maintainability.md`](docs/maintainability.md)
- [`docs/chaos-and-concurrency.md`](docs/chaos-and-concurrency.md)
- [`docs/backend-highlights.md`](docs/backend-highlights.md)
- [`docs/load-test.md`](docs/load-test.md)（压测结果）

## 结构要点
- `app/services/` 业务层；`app/routes/shop.py`、`admin_*.py` 薄路由
- 订单状态机 + `activity_logs` 审计
- Redis 缓存与结账幂等 / `FOR UPDATE` 库存

## CI & daily refresh

- CI: [.github/workflows/ci.yml](.github/workflows/ci.yml) — pytest + optional ruff on push/PR to `main`.
- Logging: [docs/logging.md](docs/logging.md) (JSON + `request_id`).
- 刷数模拟: [docs/ops-daily-refresh.md](docs/ops-daily-refresh.md) — `python scripts/simulate_daily_ops.py`

