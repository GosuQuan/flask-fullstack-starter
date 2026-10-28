"""Unit tests for checkout helpers (no DB)."""
from decimal import Decimal
from types import SimpleNamespace

from app.services.cart_checkout import cart_total


def test_cart_total_sums_active_only():
    items = [
        SimpleNamespace(
            quantity=2,
            product=SimpleNamespace(price=Decimal("10.00"), is_active=True),
        ),
        SimpleNamespace(
            quantity=1,
            product=SimpleNamespace(price=Decimal("5.00"), is_active=False),
        ),
        SimpleNamespace(quantity=3, product=None),
    ]
    assert cart_total(items) == Decimal("20.00")


def test_cart_total_empty():
    assert cart_total([]) == Decimal("0.00")
