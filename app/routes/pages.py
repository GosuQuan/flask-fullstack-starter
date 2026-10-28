"""Page routes — Jinja templates."""
from flask import Blueprint, render_template
from flask_login import login_required, current_user

pages_bp = Blueprint("pages", __name__)


@pages_bp.get("/")
def index():
    return render_template("index.html")


@pages_bp.get("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html", user=current_user)


@pages_bp.get("/interview")
def interview():
    """Public demo page with a few Flask+DB interview Q&As."""
    return render_template("interview.html")
