# Chaos 与并发

## Redis
- 默认 `REDIS_URL=redis://127.0.0.1:6379/0`
- 缓存键：`mall:product:*`、`mall:products:*`、`mall:categories:all`
- 管理端写类目/商品 → `invalidate_catalog_cache`
- Redis 不可用或 force_down → 自动降级查 DB，响应头可能无 HIT

## 触发 Chaos（需 admin 登录）
| 场景 | 方式 |
|------|------|
| Redis Down | POST `/admin/chaos/redis-down` enable=1；浏览 `/shop` 仍可用 |
| Redis 恢复 | 同上 enable=0 |
| DB 失败 | GET `/admin/chaos/db-fail` → 503 JSON |
| 库存竞态 | 结账 POST `/checkout?chaos=oos` |
| 重复结账 | 同一 `idempotency_key` 提交两次 → 「重复提交」 |

## 并发扣库存
`cart_checkout.checkout`：事务内 `SELECT ... FOR UPDATE` 后再减 `stock`。
幂等：`mall:checkout:idem:{user}:{key}` Redis SET NX。
