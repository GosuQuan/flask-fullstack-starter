"""Dev-only chaos / exception simulation (admin)."""
from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for
from flask_login import login_required

from app.decorators import admin_required
from app.extensions import db
from app.services import redis_client

admin_chaos_bp = Blueprint("admin_chaos", __name__, url_prefix="/admin/chaos")


@admin_chaos_bp.get("/")
@login_required
@admin_required
def index():
    return render_template("admin/chaos.html")


@admin_chaos_bp.post("/redis-down")
@login_required
@admin_required
def redis_down():
    flag = request.form.get("enable") == "1"
    redis_client.set_force_down(flag)
    flash(f"Redis force_down = {flag}（缓存将降级到 DB）", "warning")
    return redirect(url_for("admin_chaos.index"))


@admin_chaos_bp.get("/db-fail")
@login_required
@admin_required
def db_fail():
    """Simulate DB failure by running a bogus statement."""
    try:
        from sqlalchemy import text
        db.session.execute(text("SELECT * FROM __no_such_table__"))
        db.session.commit()
    except Exception as e:  # noqa: BLE001
        db.session.rollback()
        return jsonify({"ok": False, "simulated": "db_fail", "error": str(e)}), 503
    return jsonify({"ok": True})


@admin_chaos_bp.get("/redis-ping")
@login_required
@admin_required
def redis_ping():
    r = redis_client.get_redis()
    if not r:
        return jsonify({"ok": False, "redis": None, "force_down": True}), 503
    try:
        return jsonify({"ok": True, "pong": r.ping()})
    except Exception as e:  # noqa: BLE001
        return jsonify({"ok": False, "error": str(e)}), 503
