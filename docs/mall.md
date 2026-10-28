# 商城说明

## 前台
- `/shop` 首页
- `/shop/c/<slug>` 类目分页
- `/shop/p/<slug>` 详情 + 加购（需登录）
- `/cart` `/checkout` `/orders`

## 后台（admin）
- `/admin/categories` 类目 CRUD
- `/admin/products` 商品 CRUD
- `/admin/orders` 订单 + 状态机
- `/admin/users` 用户（原有）
- `/admin/chaos` 异常模拟

## 种子
- 管理员 `admin` / `admin123`
- 自动种子若干类目与商品（仅空库时）

## 技术
- PostgreSQL 持久化；Redis 缓存商品列表/详情（TTL，写失效）
- 结账：`SELECT FOR UPDATE` 扣库存 + Redis NX 幂等键
