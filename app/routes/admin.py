"""Admin backend — /admin/* with user CRUD + perf touches."""
from __future__ import annotations

import time

from flask import (
    Blueprint,
    flash,
    g,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required
from sqlalchemy import func, select
from sqlalchemy.orm import load_only

from app.cache_util import STATS_CACHE_KEY, cache_get, cache_invalidate, cache_set
from app.decorators import admin_required
from app.extensions import db
from app.models import User

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

PAGE_SIZE = 10


@admin_bp.before_request
def _admin_timing_start():
    g._admin_t0 = time.perf_counter()
    g._admin_query_count = 0


@admin_bp.after_request
def _admin_timing_header(response):
    t0 = getattr(g, "_admin_t0", None)
    if t0 is not None:
        ms = (time.perf_counter() - t0) * 1000
        response.headers["X-Admin-Response-Time-Ms"] = f"{ms:.2f}"
        response.headers["X-Admin-Cache"] = getattr(g, "_admin_stats_cache", "-")
    return response


def _invalidate_stats():
    cache_invalidate(STATS_CACHE_KEY)


def _get_dashboard_stats():
    cached = cache_get(STATS_CACHE_KEY)
    if cached is not None:
        g._admin_stats_cache = "HIT"
        return cached

    g._admin_stats_cache = "MISS"
    # Efficient scalar counts (no full entity load).
    user_count = db.session.scalar(select(func.count()).select_from(User)) or 0
    admin_count = (
        db.session.scalar(
            select(func.count()).select_from(User).where(User.is_admin.is_(True))
        )
        or 0
    )
    recent = db.session.scalars(
        select(User)
        .options(load_only(User.id, User.username, User.is_admin, User.created_at))
        .order_by(User.created_at.desc())
        .limit(8)
    ).all()
    payload = {
        "user_count": user_count,
        "admin_count": admin_count,
        "recent_users": recent,
    }
    # Cache counts only (ORM instances shouldn't live across requests long).
    cache_set(
        STATS_CACHE_KEY,
        {
            "user_count": user_count,
            "admin_count": admin_count,
            "recent_ids": [u.id for u in recent],
        },
        ttl_seconds=15.0,
    )
    return payload


def _stats_for_template():
    raw = _get_dashboard_stats()
    if "recent_users" in raw:
        return raw
    # Rebuild recent from cached ids (ordered).
    ids = raw.get("recent_ids") or []
    by_id = {}
    if ids:
        rows = db.session.scalars(
            select(User)
            .options(load_only(User.id, User.username, User.is_admin, User.created_at))
            .where(User.id.in_(ids))
        ).all()
        by_id = {u.id: u for u in rows}
    recent = [by_id[i] for i in ids if i in by_id]
    return {
        "user_count": raw["user_count"],
        "admin_count": raw["admin_count"],
        "recent_users": recent,
    }


@admin_bp.get("/")
@login_required
@admin_required
def dashboard():
    stats = _stats_for_template()
    return render_template(
        "admin/dashboard.html",
        user_count=stats["user_count"],
        admin_count=stats["admin_count"],
        recent_users=stats["recent_users"],
        cache_status=getattr(g, "_admin_stats_cache", "-"),
    )


@admin_bp.get("/users")
@login_required
@admin_required
def users():
    page = max(1, request.args.get("page", 1, type=int) or 1)
    q = (request.args.get("q") or "").strip()

    stmt = select(User).options(
        load_only(User.id, User.username, User.is_admin, User.created_at)
    )
    count_stmt = select(func.count()).select_from(User)

    if q:
        # Indexed username column — prefix/equality friendly; ILIKE still usable for demo.
        like = f"%{q}%"
        stmt = stmt.where(User.username.ilike(like))
        count_stmt = count_stmt.where(User.username.ilike(like))

    total = db.session.scalar(count_stmt) or 0
    pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    if page > pages:
        page = pages

    rows = db.session.scalars(
        stmt.order_by(User.id.asc()).offset((page - 1) * PAGE_SIZE).limit(PAGE_SIZE)
    ).all()

    return render_template(
        "admin/users.html",
        users=rows,
        page=page,
        pages=pages,
        total=total,
        q=q,
        page_size=PAGE_SIZE,
    )


@admin_bp.get("/users/new")
@login_required
@admin_required
def user_create():
    return render_template("admin/user_form.html", mode="create", user=None)


@admin_bp.post("/users/new")
@login_required
@admin_required
def user_create_post():
    username = (request.form.get("username") or "").strip()
    password = request.form.get("password") or ""
    is_admin = bool(request.form.get("is_admin"))

    if not username or len(username) < 3 or len(username) > 64:
        flash("用户名长度需在 3–64 之间。", "error")
        return redirect(url_for("admin.user_create"))
    if len(password) < 6:
        flash("密码至少 6 位。", "error")
        return redirect(url_for("admin.user_create"))
    if User.query.filter_by(username=username).first():
        flash("用户名已存在。", "error")
        return redirect(url_for("admin.user_create"))

    user = User(username=username, is_admin=is_admin)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    _invalidate_stats()
    flash(f"已创建用户 {username}。", "success")
    return redirect(url_for("admin.user_detail", user_id=user.id))


@admin_bp.get("/users/<int:user_id>")
@login_required
@admin_required
def user_detail(user_id: int):
    user = db.session.get(User, user_id)
    if user is None:
        flash("用户不存在。", "error")
        return redirect(url_for("admin.users"))
    return render_template("admin/user_detail.html", user=user)


@admin_bp.get("/users/<int:user_id>/edit")
@login_required
@admin_required
def user_edit(user_id: int):
    user = db.session.get(User, user_id)
    if user is None:
        flash("用户不存在。", "error")
        return redirect(url_for("admin.users"))
    return render_template("admin/user_form.html", mode="edit", user=user)


@admin_bp.post("/users/<int:user_id>/edit")
@login_required
@admin_required
def user_edit_post(user_id: int):
    user = db.session.get(User, user_id)
    if user is None:
        flash("用户不存在。", "error")
        return redirect(url_for("admin.users"))

    username = (request.form.get("username") or "").strip()
    password = request.form.get("password") or ""
    want_admin = bool(request.form.get("is_admin"))

    if not username or len(username) < 3 or len(username) > 64:
        flash("用户名长度需在 3–64 之间。", "error")
        return redirect(url_for("admin.user_edit", user_id=user_id))

    clash = User.query.filter(User.username == username, User.id != user.id).first()
    if clash:
        flash("用户名已被占用。", "error")
        return redirect(url_for("admin.user_edit", user_id=user_id))

    # Admin flag guards
    if user.is_admin and not want_admin:
        if user.id == current_user.id:
            flash("不能取消自己的管理员权限。", "error")
            return redirect(url_for("admin.user_edit", user_id=user_id))
        admin_count = (
            db.session.scalar(
                select(func.count()).select_from(User).where(User.is_admin.is_(True))
            )
            or 0
        )
        if admin_count <= 1:
            flash("不能取消最后一个管理员。", "error")
            return redirect(url_for("admin.user_edit", user_id=user_id))

    user.username = username
    user.is_admin = want_admin
    if password:
        if len(password) < 6:
            flash("新密码至少 6 位（留空则不修改）。", "error")
            return redirect(url_for("admin.user_edit", user_id=user_id))
        user.set_password(password)

    db.session.commit()
    _invalidate_stats()
    flash("用户已更新。", "success")
    return redirect(url_for("admin.user_detail", user_id=user.id))


@admin_bp.post("/users/<int:user_id>/toggle-admin")
@login_required
@admin_required
def toggle_admin(user_id: int):
    target = db.session.get(User, user_id)
    if target is None:
        flash("用户不存在。", "error")
        return redirect(url_for("admin.users"))

    if target.id == current_user.id and target.is_admin:
        flash("不能取消自己的管理员权限。", "error")
        return redirect(url_for("admin.users"))

    if target.is_admin:
        admin_count = (
            db.session.scalar(
                select(func.count()).select_from(User).where(User.is_admin.is_(True))
            )
            or 0
        )
        if admin_count <= 1:
            flash("不能取消最后一个管理员。", "error")
            return redirect(url_for("admin.users"))
        target.is_admin = False
        flash(f"已取消 {target.username} 的管理员权限。", "success")
    else:
        target.is_admin = True
        flash(f"已将 {target.username} 设为管理员。", "success")

    db.session.commit()
    _invalidate_stats()
    return redirect(url_for("admin.users", page=request.args.get("page"), q=request.args.get("q")))


@admin_bp.post("/users/<int:user_id>/delete")
@login_required
@admin_required
def delete_user(user_id: int):
    target = db.session.get(User, user_id)
    if target is None:
        flash("用户不存在。", "error")
        return redirect(url_for("admin.users"))

    if target.id == current_user.id:
        flash("不能删除当前登录账号。", "error")
        return redirect(url_for("admin.users"))

    if target.is_admin:
        admin_count = (
            db.session.scalar(
                select(func.count()).select_from(User).where(User.is_admin.is_(True))
            )
            or 0
        )
        if admin_count <= 1:
            flash("不能删除最后一个管理员。", "error")
            return redirect(url_for("admin.users"))

    name = target.username
    db.session.delete(target)
    db.session.commit()
    _invalidate_stats()
    flash(f"已删除用户 {name}。", "success")
    return redirect(url_for("admin.users"))
