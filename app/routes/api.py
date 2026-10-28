"""JSON API routes."""
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

api_bp = Blueprint("api", __name__)


@api_bp.get("/health")
def health():
    return jsonify(
        {
            "status": "ok",
            "service": "flask-fullstack-starter",
            "time": datetime.now(timezone.utc).isoformat(),
        }
    )


@api_bp.get("/hello")
def hello():
    name = "World"
    q = request.args.get("name", "").strip()
    if q:
        name = q
    return jsonify(
        {
            "message": f"Hello, {name}!",
            "from": "Flask API",
        }
    )


@api_bp.get("/me")
def me():
    if not current_user.is_authenticated:
        return jsonify({"error": "unauthorized", "message": "未登录"}), 401
    return jsonify({"user": current_user.to_dict()})
