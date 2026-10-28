# Flask + 数据库 · 面试问答（对照本项目）

> 路径：`docs/interview-flask-db.md`  
> 在线摘录页：`/interview`  
> 本文件围绕 **flask-fullstack-starter** 里真实出现的代码（`create_app`、Blueprint、PostgreSQL、Flask-Login、Werkzeug hash 等）整理常见面试题。

---

## 1. 应用结构

### Q1: 什么是 Application Factory？为什么要用 `create_app`？

**答：** 用函数创建 Flask 实例，而不是模块顶层全局 `app = Flask(__name__)`。好处：

- 测试时可多次创建、注入不同配置
- 扩展（SQLAlchemy / Login）可「先声明后 init」
- 避免循环导入

**本项目：** `app/__init__.py` 的 `create_app()`，在其中 `db.init_app(app)`、`login_manager.init_app(app)`，再注册 Blueprint。

### Q2: Blueprint 解决什么问题？

**答：** 把路由按业务拆到不同模块（页面 / API / 认证），各自有 `url_prefix`，便于多人协作和蓝绿扩展。

**本项目：**

| Blueprint | 文件 | 前缀 |
|-----------|------|------|
| pages | `app/routes/pages.py` | `/` |
| auth | `app/routes/auth.py` | `/`（`/login` `/register` `/logout`） |
| api | `app/routes/api.py` | `/api` |

---

## 2. 数据库与 ORM

### Q3: SQLAlchemy ORM 和裸 SQL 怎么选？

**答：**

| | ORM | 裸 SQL / Core |
|--|-----|---------------|
| 优势 | 对象映射、迁移友好、参数绑定防注入 | 复杂分析 SQL、性能极致可控 |
| 代价 | 抽象泄漏（N+1）、学习曲线 | 手写多、方言差异 |

**本项目：** 用 Flask-SQLAlchemy 的 `User` 模型（`app/models/user.py`）和 `db.session`。面试可说：CRUD 走 ORM；报表再 `db.session.execute(text(...))`。

### Q4: 连接池是什么？为什么需要？

**答：** 数据库连接创建贵。连接池复用 TCP + 认证后的连接。SQLAlchemy Engine 默认有 QueuePool。

**本项目：** `SQLALCHEMY_ENGINE_OPTIONS={"pool_pre_ping": True}` — 取连接前 ping，避免拿到已被服务端关掉的连接（常见于 Postgres / 云 RDS）。

### Q5: `db.create_all()` 和 Alembic 迁移有何不同？

**答：**

- `create_all`：只创建**还不存在**的表，**不会**改已有列/约束
- Alembic / Flask-Migrate：版本化 revision，可 upgrade/downgrade，适合团队与生产

**本项目：** 启动时在 `create_app` 里 `db.create_all()` 方便 demo；正式项目应上迁移。

### Q6: 事务怎么理解？Flask-SQLAlchemy 里何时 commit？

**答：** 一组操作要么全成功要么全回滚（ACID 的 A）。写操作后要 `db.session.commit()`；异常时 `rollback()`。

**本项目：** 注册用户时 `db.session.add(user)` + `commit()`（`app/routes/auth.py`）。

### Q7: 什么是 N+1 查询？怎么避免？

**答：** 查 1 次列表，再对每条关联对象各查 1 次 = 1+N。用 `joinedload` / `selectinload`，或一次 JOIN。

本 demo 无关联查询，但面试常考：列表页展示用户+文章时要 eager load。

### Q8: 索引什么时候加？有什么代价？

**答：** 高频过滤/JOIN/排序列加索引（本项目 `username` 有 `unique=True` + `index=True`）。代价：写入变慢、占空间。主键默认有索引。

### Q9: 如何防 SQL 注入？

**答：** 永远不要把用户输入拼进 SQL 字符串。ORM / 参数绑定（`:name` / `?`）会转义。本项目登录用 `User.query.filter_by(username=...)`，密码走 hash 比对，不拼 SQL。

### Q10: PostgreSQL vs SQLite？

| | PostgreSQL | SQLite |
|--|------------|--------|
| 并发写 | 强（MVCC） | 文件锁，写串行 |
| 类型/约束 | 丰富 | 弱类型 |
| 部署 | 需服务进程 | 单文件 |
| 场景 | Web 多用户、接近生产 | 本地原型、嵌入式 |

**本项目强制 Postgres**（`DATABASE_URL=postgresql+psycopg2://...`），不回退 SQLite，避免「本地能跑、上线翻车」。

---

## 3. 认证与安全

### Q11: 为什么密码要 hash？用什么算法？

**答：** 库泄露时不能直接拿到明文。Werkzeug 默认 pbkdf2（或 scrypt，视版本），带 salt。

**本项目：** `User.set_password` / `check_password` → `generate_password_hash` / `check_password_hash`。

### Q12: Flask-Login 的 session 里存什么？

**答：** 通常只存用户 id；请求时通过 `@login_manager.user_loader` 从 DB 加载。Cookie 由 Flask 用 `SECRET_KEY` 签名。

**本项目：** `load_user` 在 `create_app`；`login_user` / `logout_user` 在 auth 路由；`@login_required` 保护 `/dashboard`。

### Q13: `SECRET_KEY` 泄露会怎样？

**答：** 攻击者可伪造 session cookie，冒充任意已登录用户。生产必须用强随机环境变量，禁止提交到 Git。

**本项目：** `.env` 读入；`.env.example` 给模板；`.gitignore` 忽略 `.env`。

### Q14: `@login_required` 和 API 的 401 有何区别？

**答：** 页面路由重定向到 `login_view`（本项目 `auth.login`）并 flash；JSON API 常直接返回 401。

**本项目：** `GET /api/me` 未登录返回 `401` JSON；`/dashboard` 走 LoginManager 重定向。

---

## 4. 运维与工程

### Q15: 配置从哪里来？

**答：** 12-factor：环境变量优先。本项目 `python-dotenv` 加载根目录 `.env`，`DATABASE_URL` / `SECRET_KEY` 注入 `app.config`。

### Q16: 健康检查为什么要单独接口？

**答：** 负载均衡 / K8s probe 用。本项目 `GET /api/health` 不查库（可扩展为 ping DB）。

---

## 5. 对照速查（代码地图）

| 概念 | 位置 |
|------|------|
| 工厂 / create_all | `app/__init__.py` |
| db / LoginManager | `app/extensions.py` |
| User 模型 + hash | `app/models/user.py` |
| 注册登录登出 | `app/routes/auth.py` |
| 受保护页 | `app/routes/pages.py` → `/dashboard` |
| `/api/me` | `app/routes/api.py` |
| 环境变量样例 | `.env.example` |

更多可展开题：乐观锁、隔离级别、读写分离、连接泄漏排查、CSRF（表单可加 Flask-WTF）——本脚手架未全覆盖，面试提到「知道边界」即可。
