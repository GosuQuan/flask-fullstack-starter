"""Schema ensure + demo seed (local only)."""
from __future__ import annotations

import logging
from decimal import Decimal

from sqlalchemy import inspect, text

from app.extensions import db
from app.models import Category, Product, User

logger = logging.getLogger(__name__)

DEMO_ADMIN_USERNAME = "admin"
DEMO_ADMIN_PASSWORD = "admin123"


def ensure_schema() -> None:
    # Import all models so metadata is complete
    import app.models  # noqa: F401

    db.create_all()
    _ensure_users_is_admin_column()
    _ensure_created_at_index()


def _ensure_users_is_admin_column() -> None:
    insp = inspect(db.engine)
    if "users" not in insp.get_table_names():
        return
    cols = {c["name"] for c in insp.get_columns("users")}
    if "is_admin" in cols:
        return
    db.session.execute(
        text(
            "ALTER TABLE users "
            "ADD COLUMN IF NOT EXISTS is_admin BOOLEAN NOT NULL DEFAULT FALSE"
        )
    )
    db.session.commit()


def _ensure_created_at_index() -> None:
    insp = inspect(db.engine)
    if "users" not in insp.get_table_names():
        return
    existing = {ix["name"] for ix in insp.get_indexes("users")}
    if "ix_users_created_at" in existing:
        return
    db.session.execute(
        text("CREATE INDEX IF NOT EXISTS ix_users_created_at ON users (created_at)")
    )
    db.session.commit()


def seed_demo_admin() -> None:
    try:
        has_admin = (
            db.session.query(User.id).filter_by(is_admin=True).first() is not None
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("seed_demo_admin skipped: %s", exc)
        return
    if has_admin:
        return
    existing = User.query.filter_by(username=DEMO_ADMIN_USERNAME).first()
    if existing:
        existing.is_admin = True
        db.session.commit()
        return
    user = User(username=DEMO_ADMIN_USERNAME, is_admin=True)
    user.set_password(DEMO_ADMIN_PASSWORD)
    db.session.add(user)
    db.session.commit()
    logger.info("Seeded demo admin admin/admin123")


def seed_mall_demo() -> None:
    """Seed categories + products once."""
    if Category.query.first() is not None:
        return
    cats = [
        Category(name="数码配件", slug="gadgets", sort_order=1),
        Category(name="生活家居", slug="home", sort_order=2),
        Category(name="文创周边", slug="culture", sort_order=3),
    ]
    db.session.add_all(cats)
    db.session.flush()
    products = [
        Product(
            category_id=cats[0].id,
            name="机械键盘 K87",
            slug="mech-keyboard-k87",
            description="87 键热插拔机械键盘，演示商品。",
            price=Decimal("299.00"),
            stock=50,
            is_active=True,
            cover_url="",
        ),
        Product(
            category_id=cats[0].id,
            name="无线鼠标 M2",
            slug="wireless-mouse-m2",
            description="静音无线鼠标。",
            price=Decimal("89.00"),
            stock=120,
            is_active=True,
        ),
        Product(
            category_id=cats[0].id,
            name="USB-C 扩展坞",
            slug="usbc-hub",
            description="7 合 1 扩展坞。",
            price=Decimal("159.00"),
            stock=40,
            is_active=True,
        ),
        Product(
            category_id=cats[1].id,
            name="保温水杯 500ml",
            slug="thermo-bottle-500",
            description="不锈钢保温杯。",
            price=Decimal("69.00"),
            stock=80,
            is_active=True,
        ),
        Product(
            category_id=cats[1].id,
            name="香薰蜡烛套装",
            slug="scented-candle-set",
            description="三支装香薰蜡烛。",
            price=Decimal("128.00"),
            stock=35,
            is_active=True,
        ),
        Product(
            category_id=cats[2].id,
            name="帆布托特包",
            slug="canvas-tote",
            description="文创帆布包。",
            price=Decimal("59.00"),
            stock=90,
            is_active=True,
        ),
        Product(
            category_id=cats[2].id,
            name="贴纸礼盒",
            slug="sticker-box",
            description="手帐贴纸合集。",
            price=Decimal("39.00"),
            stock=200,
            is_active=True,
        ),
    ]
    db.session.add_all(products)
    db.session.commit()
    logger.info("Seeded mall demo categories/products")
