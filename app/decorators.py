"""Authz helpers."""
from functools import wraps

from flask import abort, flash, redirect, url_for
from flask_login import current_user


def admin_required(view):
    """Require login + is_admin; anonymous -> login, non-admin -> 403."""

    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated:
            flash("请先登录后再访问管理后台。", "warning")
            return redirect(url_for("auth.login", next="/admin"))
        if not getattr(current_user, "is_admin", False):
            abort(403)
        return view(*args, **kwargs)

    return wrapped
