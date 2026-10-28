"""Admin orders + status workflow."""
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required

from app.decorators import admin_required
from app.extensions import db
from app.models import Order
from app.services.audit import log_action
from app.services.order_workflow import InvalidTransition, transition

admin_orders_bp = Blueprint("admin_orders", __name__, url_prefix="/admin")


@admin_orders_bp.get("/orders")
@login_required
@admin_required
def orders():
    rows = Order.query.order_by(Order.id.desc()).limit(100).all()
    return render_template("admin/orders.html", orders=rows)


@admin_orders_bp.get("/orders/<int:oid>")
@login_required
@admin_required
def order_detail(oid):
    order = db.session.get(Order, oid)
    if not order:
        flash("订单不存在。", "error")
        return redirect(url_for("admin_orders.orders"))
    return render_template("admin/order_detail.html", order=order)


@admin_orders_bp.post("/orders/<int:oid>/status")
@login_required
@admin_required
def order_status(oid):
    order = db.session.get(Order, oid)
    if not order:
        flash("订单不存在。", "error")
        return redirect(url_for("admin_orders.orders"))
    new_status = (request.form.get("status") or "").strip()
    try:
        old = order.status
        transition(order, new_status)
        log_action("order.status", "order", order.id, f"{old}->{new_status}")
        db.session.commit()
        flash(f"状态已更新：{old} → {new_status}", "success")
    except InvalidTransition as e:
        db.session.rollback()
        flash(f"非法流转: {e}", "error")
    return redirect(url_for("admin_orders.order_detail", oid=oid))
