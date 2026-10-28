[![CI](https://github.com/GosuQuan/flask-fullstack-starter/actions/workflows/ci.yml/badge.svg)](https://github.com/GosuQuan/flask-fullstack-starter/actions/workflows/ci.yml)

# Flask Mall Starter

可演示的开源商城起步项目：前台逛店 / 加购 / 下单，后台管类目、商品、订单、用户。  
**Stack:** Flask + PostgreSQL + Redis + Flask-Login（英文一句话：a maintainable Flask mall demo with cache, locked checkout, and chaos hooks）.

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
- 健康检查：http://127.0.0.1:5000/api/health

复制 `.env.example` → `.env` 后按需改 `DATABASE_URL` / `REDIS_URL` / `SECRET_KEY`。**不要提交 `.env`。**

## 技术方案（大白话）

这是一个**可演示的开源商城起步项目**：前台能逛店、加购、下单；后台能管类目、商品、订单、用户。技术栈很直白——**Flask 做 Web，PostgreSQL 存数据，Redis 做缓存和结账幂等**，业务逻辑尽量不写在路由里，方便以后加功能、也方便面试时讲清楚「为什么这样拆」。

### 整体怎么分层

| 层 | 干什么 | 放哪 |
|----|--------|------|
| 路由（薄） | 收参数、鉴权、跳转、闪消息 | `app/routes/` |
| 业务（厚） | 真正规则：库存、状态流转、缓存、审计 | `app/services/` |
| 模型 | 表结构与关系 | `app/models/` |
| 扩展 / 启动 | DB、Login、种子数据、Schema 补丁 | `app/extensions.py`、`bootstrap.py`、`create_app` |

**可维护性**靠的是：改业务找 `services/`，改页面找 `templates/`，新增一个后台模块就「模型 → service（带审计 + 缓存失效）→ 独立 Blueprint → 注册 → 模板」这一套，而不是把 SQL 和状态判断堆在路由里。

### 为什么能扛一点并发

结账是最容易翻车的地方（超卖、重复点两次）。这里做了两件事：

1. **库存锁**：事务里对商品行 `SELECT … FOR UPDATE`，锁住再扣 `stock`，同一时刻别的结账要等，避免两个请求都以为「还有货」。
2. **幂等键**：可选 `idempotency_key`，用 Redis `SET NX`（键形如 `mall:checkout:idem:{user}:{key}`，短 TTL）。同一用户同一 key 再提交，直接拒绝「重复结账」，而不是再下一单。

路由层保持薄；真正逻辑在 `app/services/cart_checkout.py`。管理端还有 Chaos 开关（Redis 挂掉、DB 失败、模拟库存不足、重复结账），方便演示「坏了会怎样、系统会不会硬挂」。

### 缓存怎么用、写了怎么失效

商品列表 / 详情 / 类目读多写少，走 Redis：

- 键约定：`mall:product:*`、`mall:products:*`、`mall:categories:all`
- 读：先查缓存，有就 HIT，没有查库再写入（带 TTL）
- **写失效**：后台改类目或商品后调用 `invalidate_catalog_cache()`，按 pattern 删相关键，避免用户看到过期价/过期库存列表
- Redis 不可用或 Chaos「Redis Down」时：**自动降级查 DB**，商城还能逛，而不是整站 500

另外，管理后台仪表盘有一小段**进程内 TTL 缓存**（`cache_util.py`），演示「读多写少热点 + 写后失效」；多进程/多机时要换成共享缓存，面试里可以主动讲这点。

### 订单状态机（不允许乱跳）

状态写在 `app/services/order_workflow.py`，用一张允许表约束流转，非法跳转抛 `InvalidTransition`：

```text
pending  → paid | cancelled
paid     → shipped | cancelled
shipped  → completed
completed / cancelled → （终态，不能再变）
```

后台改订单状态走这套，而不是随便改字符串。重要操作还会写进 `activity_logs`（`audit.log_action`），方便事后查「谁在什么时候改了什么」。

### 数据与工程边界（诚实说）

- 持久化：PostgreSQL；连接池 `pool_pre_ping`
- Schema：`create_all` + 启动时检查缺列/缺索引再 `ALTER` / `CREATE INDEX`（无 Alembic 时的权宜；生产应上 Flask-Migrate）
- 鉴权：Flask-Login；后台再加 `admin_required`；密码 Werkzeug 哈希
- Demo 账号 `admin` / `admin123` **仅本地**；`SECRET_KEY`、`.env` 不要提交
- 压测：仓库带 Locust 与 `docs/load-test.md`，可对照并发与失败形态

更细的说明见：`docs/mall.md`、`docs/maintainability.md`、`docs/chaos-and-concurrency.md`、`docs/backend-highlights.md`。

## 目录说明（每个目录/关键文件干什么）

```text
flask-fullstack-starter/
├── run.py / wsgi.py          # 本地启动 / WSGI 入口
├── requirements.txt          # Python 依赖
├── locustfile.py             # Locust 压测脚本
├── .env.example              # 环境变量模板（DATABASE_URL、REDIS_URL 等）
├── README.md                 # 快速开始 + 本文档
├── data/                     # 日常刷数用的上游 CSV / 库存 baseline
├── scripts/                  # 夜间刷数 / 对账 / 流程模拟
├── tests/                    # pytest（health、购物车 helper）
├── .github/workflows/ci.yml  # CI：安装依赖 + pytest
├── docs/                     # 专题说明与压测报告
└── app/                      # 应用主体
    ├── __init__.py           # create_app：配置、日志、注册蓝图、启动种子
    ├── logging_util.py       # JSON 结构化日志 + request_id
    ├── bootstrap.py          # Schema 补丁 + demo 管理员/商城种子数据
    ├── extensions.py         # db、login_manager
    ├── decorators.py         # admin_required 等
    ├── cache_util.py         # 管理端进程内短 TTL 缓存
    ├── utils_slug.py         # slug 生成
    ├── models/               # 表：User、类目/商品/购物车/订单、审计日志等
    ├── services/             # 业务核心（见下）
    ├── routes/               # 薄路由蓝图（见下）
    ├── templates/            # Jinja 模板（shop / admin / auth / errors）
    └── static/               # CSS / JS
```

### `app/services/`（最该看的地方）

| 文件 | 职责 |
|------|------|
| `catalog.py` | 类目/商品查询、Redis 缓存读写、`invalidate_catalog_cache` |
| `cart_checkout.py` | 购物车 + 结账；`FOR UPDATE` 扣库存；Redis NX 幂等 |
| `order_workflow.py` | 订单状态机允许表与 `transition` |
| `audit.py` | `log_action` → `activity_logs` |
| `redis_client.py` | Redis 封装；不可用时安全降级 |

### `app/routes/`（只做 HTTP 胶水）

| 文件 | 职责 |
|------|------|
| `shop.py` | 前台商城、购物车、结账、我的订单 |
| `admin.py` | 后台用户 CRUD、仪表盘 |
| `admin_catalog.py` | 类目 / 商品 CRUD（写后失效缓存） |
| `admin_orders.py` | 订单列表/详情 + 状态流转 |
| `admin_chaos.py` | Chaos：Redis Down、DB fail、结账异常演示 |
| `auth.py` / `pages.py` / `api.py` | 登录注册、静态页、少量 API |

**一句话总结**：路由薄、业务集中在 services；读靠 Redis + 写失效，写订单靠行锁 + 幂等；订单只能按状态机走，关键操作有审计——作品集里讲「可维护 / 并发 / 缓存 / 状态机」都能对着代码指出来。

## 日常刷数（模拟）

夜间同步上游目录、软删过期 SKU、对账库存漂移：

```powershell
python scripts/simulate_daily_ops.py
# 或分步：
python scripts/refresh_catalog.py --csv data/catalog_upstream.csv
python scripts/reconcile_stock.py --baseline data/stock_baseline.csv
```

说明：[docs/ops-daily-refresh.md](docs/ops-daily-refresh.md)

## CI & 日志

- CI：[.github/workflows/ci.yml](.github/workflows/ci.yml) — push/PR 到 `main` 跑 pytest（可选 ruff）
- 结构化日志：[docs/logging.md](docs/logging.md)（JSON + `X-Request-ID`）

## 文档索引

- [docs/mall.md](docs/mall.md) — 商城路由与种子
- [docs/maintainability.md](docs/maintainability.md) — 分层与扩展方式
- [docs/chaos-and-concurrency.md](docs/chaos-and-concurrency.md) — Chaos / 并发
- [docs/backend-highlights.md](docs/backend-highlights.md) — 后端亮点
- [docs/load-test.md](docs/load-test.md) — Locust 压测结果
- [docs/logging.md](docs/logging.md) / [docs/ops-daily-refresh.md](docs/ops-daily-refresh.md)

## 作品集可写的亮点

1. **薄路由 + services 分层**，后台新模块有固定扩展路径  
2. **结账 `FOR UPDATE` + Redis NX 幂等**，并可用 Chaos 演示失败形态  
3. **Redis 读缓存 + 写失效 + 降级**，缓存挂了店还能逛  
4. **订单状态机 + activity_logs 审计**  
5. **夜间刷数脚本 + CI + JSON `request_id` 日志**，贴近日常运维叙事  

Public repo: https://github.com/GosuQuan/flask-fullstack-starter
