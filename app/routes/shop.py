"""Storefront — thin routes over catalog/cart services."""
import uuid
from flask import Blueprint, flash, redirect, render_template, request, url_for, g
from flask_login import current_user, login_required

from app.services import catalog
from app.services.cart_checkout import (
    CheckoutError,
    add_to_cart,
    cart_total,
    checkout,
    get_cart,
    get_order,
    list_user_orders,
    remove_cart_item,
    update_cart_item,
)

shop_bp = Blueprint("shop", __name__)


@shop_bp.after_request
def _cache_hdr(resp):
    status = getattr(g, "cache_status", None)
    if status:
        resp.headers["X-Cache"] = status
    return resp


@shop_bp.get("/shop")
def home():
    cats, _ = catalog.list_categories()
    featured, cs = catalog.list_products(page=1, page_size=8)
    g.cache_status = cs
    return render_template(
        "shop/home.html", categories=cats, products=featured["items"]
    )


@shop_bp.get("/shop/c/<slug>")
def category(slug):
    page = request.args.get("page", 1, type=int) or 1
    cats, _ = catalog.list_categories()
    data, cs = catalog.list_products(category_slug=slug, page=page)
    g.cache_status = cs
    cat = next((c for c in cats if c["slug"] == slug), None)
    return render_template(
        "shop/category.html",
        categories=cats,
        category=cat,
        products=data["items"],
        page=data["page"],
        pages=data["pages"],
        total=data["total"],
        slug=slug,
    )


@shop_bp.get("/shop/p/<slug>")
def product_detail(slug):
    data, cs = catalog.get_product_by_slug(slug)
    g.cache_status = cs
    if not data:
        flash("商品不存在或已下架。", "error")
        return redirect(url_for("shop.home"))
    return render_template("shop/product.html", product=data)


@shop_bp.post("/shop/p/<slug>/add")
@login_required
def product_add(slug):
    data, _ = catalog.get_product_by_slug(slug)
    if not data:
        flash("商品不存在。", "error")
        return redirect(url_for("shop.home"))
    qty = request.form.get("qty", 1, type=int) or 1
    try:
        add_to_cart(current_user.id, data["id"], qty)
        flash("已加入购物车。", "success")
    except CheckoutError as e:
        flash(str(e), "error")
    return redirect(url_for("shop.product_detail", slug=slug))


@shop_bp.get("/cart")
@login_required
def cart():
    items = get_cart(current_user.id)
    return render_template(
        "shop/cart.html", items=items, total=cart_total(items)
    )


@shop_bp.post("/cart/<int:item_id>/update")
@login_required
def cart_update(item_id):
    qty = request.form.get("qty", 1, type=int) or 0
    try:
        update_cart_item(current_user.id, item_id, qty)
        flash("购物车已更新。", "success")
    except CheckoutError as e:
        flash(str(e), "error")
    return redirect(url_for("shop.cart"))


@shop_bp.post("/cart/<int:item_id>/remove")
@login_required
def cart_remove(item_id):
    try:
        remove_cart_item(current_user.id, item_id)
        flash("已移除。", "success")
    except CheckoutError as e:
        flash(str(e), "error")
    return redirect(url_for("shop.cart"))


@shop_bp.route("/checkout", methods=["GET", "POST"])
@login_required
def checkout_view():
    items = get_cart(current_user.id)
    if request.method == "GET":
        return render_template(
            "shop/checkout.html",
            items=items,
            total=cart_total(items),
            idempotency_key=str(uuid.uuid4()),
        )
    idem = request.form.get("idempotency_key") or request.headers.get("X-Idempotency-Key")
    chaos_oos = request.args.get("chaos") == "oos" or request.form.get("chaos") == "oos"
    try:
        order = checkout(current_user.id, idempotency_key=idem, chaos_oos=chaos_oos)
        flash(f"下单成功，订单 #{order.id}（pending，演示无真实支付）。", "success")
        return redirect(url_for("shop.order_detail", order_id=order.id))
    except CheckoutError as e:
        flash(str(e), "error")
        return redirect(url_for("shop.cart"))


@shop_bp.get("/orders")
@login_required
def orders():
    rows = list_user_orders(current_user.id)
    return render_template("shop/orders.html", orders=rows)


@shop_bp.get("/orders/<int:order_id>")
@login_required
def order_detail(order_id):
    order = get_order(order_id)
    if not order or (order.user_id != current_user.id and not current_user.is_admin):
        flash("订单不存在。", "error")
        return redirect(url_for("shop.orders"))
    return render_template("shop/order_detail.html", order=order)
