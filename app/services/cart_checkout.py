"""Cart + concurrent-safe checkout with stock reservation."""
from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.extensions import db
from app.models import CartItem, Order, OrderItem, Product
from app.services import redis_client
from app.services.audit import log_action


class CheckoutError(Exception):
    pass


def get_cart(user_id: int):
    return db.session.scalars(
        select(CartItem)
        .options(joinedload(CartItem.product))
        .where(CartItem.user_id == user_id)
        .order_by(CartItem.id.asc())
    ).all()


def cart_total(items) -> Decimal:
    total = Decimal("0.00")
    for it in items:
        if it.product and it.product.is_active:
            total += Decimal(it.product.price) * it.quantity
    return total


def add_to_cart(user_id: int, product_id: int, qty: int = 1) -> CartItem:
    qty = max(1, int(qty))
    product = db.session.get(Product, product_id)
    if not product or not product.is_active:
        raise CheckoutError("商品不存在或已下架")
    item = db.session.scalars(
        select(CartItem).where(
            CartItem.user_id == user_id, CartItem.product_id == product_id
        )
    ).first()
    if item:
        item.quantity += qty
    else:
        item = CartItem(user_id=user_id, product_id=product_id, quantity=qty)
        db.session.add(item)
    db.session.commit()
    return item


def update_cart_item(user_id: int, item_id: int, qty: int) -> None:
    item = db.session.get(CartItem, item_id)
    if not item or item.user_id != user_id:
        raise CheckoutError("购物车项不存在")
    if qty <= 0:
        db.session.delete(item)
    else:
        item.quantity = qty
    db.session.commit()


def remove_cart_item(user_id: int, item_id: int) -> None:
    item = db.session.get(CartItem, item_id)
    if not item or item.user_id != user_id:
        raise CheckoutError("购物车项不存在")
    db.session.delete(item)
    db.session.commit()


def checkout(user_id: int, idempotency_key: str | None = None, chaos_oos: bool = False) -> Order:
    """
    Place order with:
    - Redis NX idempotency key (optional)
    - SELECT FOR UPDATE stock reservation in one transaction
    """
    if idempotency_key:
        acquired = redis_client.try_set_nx(
            f"mall:checkout:idem:{user_id}:{idempotency_key}", "1", ttl=120
        )
        if not acquired:
            raise CheckoutError("重复提交：请勿重复结账（idempotency）")

    items = get_cart(user_id)
    if not items:
        raise CheckoutError("购物车为空")

    try:
        order = Order(user_id=user_id, status="pending", total_amount=Decimal("0.00"))
        db.session.add(order)
        db.session.flush()

        total = Decimal("0.00")
        for it in items:
            # Lock product row
            product = db.session.scalars(
                select(Product).where(Product.id == it.product_id).with_for_update()
            ).first()
            if not product or not product.is_active:
                raise CheckoutError(f"商品不可用: id={it.product_id}")
            if chaos_oos:
                # Force race-like failure after lock for demo
                raise CheckoutError("chaos: 模拟超卖/库存不足")
            if product.stock < it.quantity:
                raise CheckoutError(f"库存不足: {product.name}")
            product.stock -= it.quantity  # reserve / deduct
            line = Decimal(product.price) * it.quantity
            total += line
            db.session.add(
                OrderItem(
                    order_id=order.id,
                    product_id=product.id,
                    product_name=product.name,
                    unit_price=product.price,
                    quantity=it.quantity,
                    line_total=line,
                )
            )
            db.session.delete(it)

        order.total_amount = total
        log_action("order.checkout", "order", order.id, f"total={total}")
        db.session.commit()
        return order
    except Exception:
        db.session.rollback()
        raise


def list_user_orders(user_id: int):
    return db.session.scalars(
        select(Order)
        .where(Order.user_id == user_id)
        .order_by(Order.id.desc())
    ).all()


def get_order(order_id: int) -> Order | None:
    return db.session.scalars(
        select(Order)
        .options(joinedload(Order.items))
        .where(Order.id == order_id)
    ).first()
