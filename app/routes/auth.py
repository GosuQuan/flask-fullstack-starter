"""Auth routes: register / login / logout."""
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from app.extensions import db
from app.models import User

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("pages.dashboard"))

    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""
        password2 = request.form.get("password2") or ""

        if not username or not password:
            flash("用户名和密码不能为空。", "error")
        elif len(username) < 3 or len(username) > 64:
            flash("用户名长度需在 3–64 之间。", "error")
        elif len(password) < 6:
            flash("密码至少 6 位。", "error")
        elif password != password2:
            flash("两次输入的密码不一致。", "error")
        elif User.query.filter_by(username=username).first():
            flash("该用户名已被注册。", "error")
        else:
            user = User(username=username)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            flash("注册成功，请登录。", "success")
            return redirect(url_for("auth.login"))

    return render_template("auth/register.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("pages.dashboard"))

    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""
        remember = bool(request.form.get("remember"))

        user = User.query.filter_by(username=username).first()
        if user is None or not user.check_password(password):
            flash("用户名或密码错误。", "error")
        else:
            login_user(user, remember=remember)
            flash(f"欢迎回来，{user.username}！", "success")
            next_url = request.args.get("next")
            if next_url and next_url.startswith("/"):
                return redirect(next_url)
            return redirect(url_for("pages.dashboard"))

    return render_template("auth/login.html")


@auth_bp.post("/logout")
@login_required
def logout():
    logout_user()
    flash("已退出登录。", "success")
    return redirect(url_for("pages.index"))


@auth_bp.get("/logout")
@login_required
def logout_get():
    """Allow GET logout for simple nav links."""
    logout_user()
    flash("已退出登录。", "success")
    return redirect(url_for("pages.index"))
