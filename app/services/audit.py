"""Activity / audit logging for admin actions."""
from __future__ import annotations

from flask_login import current_user

from app.extensions import db
from app.models import ActivityLog


def log_action(action: str, entity_type: str, entity_id=None, detail: str | None = None) -> None:
    actor_id = None
    try:
        if current_user.is_authenticated:
            actor_id = current_user.id
    except Exception:
        actor_id = None
    row = ActivityLog(
        actor_user_id=actor_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        detail=detail,
    )
    db.session.add(row)
    # Caller commits with business transaction, or we flush lightly.
