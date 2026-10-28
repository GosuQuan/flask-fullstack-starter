"""Admin CRUD: categories & products."""
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required

from app.decorators import admin_required
from app.extensions import db
from app.models import Category, Product
from app.services import catalog
from app.utils_slug import slugify

admin_catalog_bp = Blueprint("admin_catalog", __name__, url_prefix="/admin")


@admin_catalog_bp.get("/categories")
@login_required
@admin_required
def categories():
    rows = Category.query.order_by(Category.sort_order.asc(), Category.id.asc()).all()
    return render_template("admin/categories.html", categories=rows)


@admin_catalog_bp.route("/categories/new", methods=["GET", "POST"])
@login_required
@admin_required
def category_new():
    if request.method == "POST":
        name = (request.form.get("name") or "").strip()
        slug = (request.form.get("slug") or "").strip()
        sort_order = request.form.get("sort_order", 0, type=int) or 0
        if not name:
            flash("名称必填。", "error")
        else:
            catalog.create_category(name, slug or None, sort_order)
            flash("类目已创建。", "success")
            return redirect(url_for("admin_catalog.categories"))
    return render_template("admin/category_form.html", mode="create", category=None)


@admin_catalog_bp.route("/categories/<int:cid>/edit", methods=["GET", "POST"])
@login_required
@admin_required
def category_edit(cid):
    cat = db.session.get(Category, cid)
    if not cat:
        flash("类目不存在。", "error")
        return redirect(url_for("admin_catalog.categories"))
    if request.method == "POST":
        catalog.update_category(
            cat,
            request.form.get("name") or cat.name,
            request.form.get("slug") or cat.slug,
            request.form.get("sort_order", cat.sort_order, type=int) or 0,
        )
        flash("类目已更新。", "success")
        return redirect(url_for("admin_catalog.categories"))
    return render_template("admin/category_form.html", mode="edit", category=cat)


@admin_catalog_bp.post("/categories/<int:cid>/delete")
@login_required
@admin_required
def category_delete(cid):
    cat = db.session.get(Category, cid)
    if not cat:
        flash("类目不存在。", "error")
    elif cat.products.count() > 0:
        flash("类目下仍有商品，无法删除。", "error")
    else:
        catalog.delete_category(cat)
        flash("类目已删除。", "success")
    return redirect(url_for("admin_catalog.categories"))


@admin_catalog_bp.get("/products")
@login_required
@admin_required
def products():
    rows = Product.query.order_by(Product.id.desc()).all()
    return render_template("admin/products.html", products=rows)


@admin_catalog_bp.route("/products/new", methods=["GET", "POST"])
@login_required
@admin_required
def product_new():
    cats = Category.query.order_by(Category.sort_order).all()
    if request.method == "POST":
        try:
            p = catalog.create_product(
                category_id=int(request.form["category_id"]),
                name=request.form.get("name") or "",
                slug=request.form.get("slug") or "",
                description=request.form.get("description") or "",
                price=request.form.get("price") or "0",
                stock=request.form.get("stock") or 0,
                is_active=bool(request.form.get("is_active")),
                cover_url=request.form.get("cover_url") or "",
            )
            flash(f"商品已创建：{p.name}", "success")
            return redirect(url_for("admin_catalog.products"))
        except Exception as e:  # noqa: BLE001
            flash(f"创建失败: {e}", "error")
    return render_template(
        "admin/product_form.html", mode="create", product=None, categories=cats
    )


@admin_catalog_bp.route("/products/<int:pid>/edit", methods=["GET", "POST"])
@login_required
@admin_required
def product_edit(pid):
    p = db.session.get(Product, pid)
    cats = Category.query.order_by(Category.sort_order).all()
    if not p:
        flash("商品不存在。", "error")
        return redirect(url_for("admin_catalog.products"))
    if request.method == "POST":
        catalog.update_product(
            p,
            category_id=int(request.form["category_id"]),
            name=request.form.get("name") or p.name,
            slug=request.form.get("slug") or p.slug,
            description=request.form.get("description") or "",
            price=request.form.get("price") or p.price,
            stock=request.form.get("stock") or p.stock,
            is_active=bool(request.form.get("is_active")),
            cover_url=request.form.get("cover_url") or "",
        )
        flash("商品已更新。", "success")
        return redirect(url_for("admin_catalog.products"))
    return render_template(
        "admin/product_form.html", mode="edit", product=p, categories=cats
    )


@admin_catalog_bp.post("/products/<int:pid>/delete")
@login_required
@admin_required
def product_delete(pid):
    p = db.session.get(Product, pid)
    if not p:
        flash("商品不存在。", "error")
    else:
        catalog.delete_product(p)
        flash("商品已删除。", "success")
    return redirect(url_for("admin_catalog.products"))
