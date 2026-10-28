"""Flask application factory."""
import os
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, render_template

load_dotenv(Path(__file__).resolve().parent.parent / ".env")


def create_app() -> Flask:
    app = Flask(
        __name__,
        template_folder="templates",
        static_folder="static",
        instance_relative_config=True,
    )

    database_url = os.environ.get(
        "DATABASE_URL",
        "postgresql+psycopg2://flask:flask@127.0.0.1:5432/flask_starter",
    )
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev-change-me"),
        JSON_AS_ASCII=False,
        SQLALCHEMY_DATABASE_URI=database_url,
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SQLALCHEMY_ENGINE_OPTIONS={"pool_pre_ping": True},
        REDIS_URL=os.environ.get("REDIS_URL", "redis://127.0.0.1:6379/0"),
    )

    from app.extensions import db, login_manager

    db.init_app(app)
    login_manager.init_app(app)

    from app.models import User

    @login_manager.user_loader
    def load_user(user_id: str):
        return db.session.get(User, int(user_id))

    from app.routes.admin import admin_bp
    from app.routes.admin_catalog import admin_catalog_bp
    from app.routes.admin_chaos import admin_chaos_bp
    from app.routes.admin_orders import admin_orders_bp
    from app.routes.api import api_bp
    from app.routes.auth import auth_bp
    from app.routes.pages import pages_bp
    from app.routes.shop import shop_bp

    app.register_blueprint(pages_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(shop_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(admin_catalog_bp)
    app.register_blueprint(admin_orders_bp)
    app.register_blueprint(admin_chaos_bp)
    app.register_blueprint(api_bp, url_prefix="/api")

    @app.errorhandler(403)
    def forbidden(_err):
        return render_template("errors/403.html"), 403

    with app.app_context():
        try:
            from app.bootstrap import ensure_schema, seed_demo_admin, seed_mall_demo

            ensure_schema()
            seed_demo_admin()
            seed_mall_demo()
        except Exception as exc:  # noqa: BLE001
            app.logger.warning(
                "Database unreachable or bootstrap failed (%s). "
                "Set DATABASE_URL and ensure PostgreSQL is running.",
                exc,
            )

    return app
