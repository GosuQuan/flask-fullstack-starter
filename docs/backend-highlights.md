# 后台性能与工程亮点（对照代码）

面向简历 / 面试口述。实现都在本仓库，不是空讲。

## 1. 管理后台范围

- 路径前缀：`/admin`（`app/routes/admin.py`）
- 鉴权：`@login_required` + `@admin_required`（`app/decorators.py`）
- 非管理员 → `403` 模板（`app/templates/errors/403.html`）
- 用户 **CRUD**：列表/详情/新建/编辑/删除 + 快捷升降管理员

本地种子管理员（**仅 demo**）：`admin` / `admin123`（`app/bootstrap.py`）

## 2. 性能相关实现

| 点 | 做法 | 代码位置 |
|----|------|----------|
| 分页 | `LIMIT/OFFSET`，每页 10 | `admin.users` |
| 搜索列有索引 | `users.username` unique+index；搜索走该列 `ILIKE` | `User` 模型 |
| 最近用户排序索引 | `ix_users_created_at`；bootstrap `CREATE INDEX IF NOT EXISTS` | `bootstrap.py` |
| 减列加载 | `load_only(id, username, is_admin, created_at)`，列表不拉 `password_hash` | `admin.users` / dashboard |
| 高效 count | `select(func.count()).select_from(User)`，不 `len(query.all())` | dashboard / users |
| PK 取单行 | `db.session.get(User, id)` | detail / edit / delete |
| 连接池探活 | `pool_pre_ping=True` | `create_app` |
| 仪表盘短缓存 | 进程内 dict+TTL(15s)；写用户后 `cache_invalidate` | `app/cache_util.py` |
| 可观测 | 响应头 `X-Admin-Response-Time-Ms`、`X-Admin-Cache` | `after_request` |

### 缓存说明（面试怎么讲）

- **不是 Redis**：单进程 TTL 字典，演示「读多写少热点 + 写时失效」。
- 多 worker / 多机需 Redis/Memcached 并定义一致的 key 与失效策略。
- HIT/MISS 通过仪表盘徽章与 `X-Admin-Cache` 可见。

### EXPLAIN 友好查询示例

列表（有搜索时）：

```sql
SELECT id, username, is_admin, created_at
FROM users
WHERE username ILIKE '%foo%'
ORDER BY id
LIMIT 10 OFFSET 0;
```

可在 `psql` 里：

```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT id, username, is_admin, created_at
FROM users
ORDER BY created_at DESC
LIMIT 8;
```

期望看到 Index Scan / Index Only Scan（视数据量与统计信息而定）。

## 3. Schema 演进（无 Alembic 时的权宜）

`create_all` **不会**改已有列。本项目用：

1. `db.create_all()`
2. `inspect` 检测列/索引缺失
3. `ALTER TABLE ... ADD COLUMN IF NOT EXISTS`
4. `CREATE INDEX IF NOT EXISTS`

生产仍应上 **Alembic / Flask-Migrate**。

## 4. 安全边界（诚实写进简历）

- 密码 Werkzeug hash；session 依赖 `SECRET_KEY`
- 管理写操作目前无 CSRF token（可加 Flask-WTF）——面试可主动提改进点
- 种子账号必须改掉；禁止提交 `.env`
