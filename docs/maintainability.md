# 可维护性说明

## 分层
- **routes/**：薄控制器（参数解析、flash、redirect）
- **services/**：业务（catalog、cart_checkout、order_workflow、audit、redis_client）
- **models/**：表结构

新增后台 CRUD 模块建议：
1. `models/` 加表
2. `services/xxx.py` 写 create/update/delete + `log_action` + 缓存失效
3. `routes/admin_xxx.py` 独立 Blueprint，`url_prefix=/admin`
4. 在 `create_app` 注册
5. 模板放 `templates/admin/`

## 订单状态机
见 `app/services/order_workflow.py`：
`pending → paid|cancelled`；`paid → shipped|cancelled`；`shipped → completed`。

## 审计日志
表 `activity_logs`（`ActivityLog`），`app/services/audit.py` 的 `log_action`。
后台改类目/商品/下单/改状态时写入。
