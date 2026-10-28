"""Explicit order status transitions."""
from __future__ import annotations

ALLOWED = {
    "pending": {"paid", "cancelled"},
    "paid": {"shipped", "cancelled"},
    "shipped": {"completed"},
    "completed": set(),
    "cancelled": set(),
}


class InvalidTransition(Exception):
    pass


def can_transition(current: str, new: str) -> bool:
    return new in ALLOWED.get(current, set())


def transition(order, new_status: str) -> None:
    if not can_transition(order.status, new_status):
        raise InvalidTransition(f"{order.status} -> {new_status} not allowed")
    order.status = new_status
