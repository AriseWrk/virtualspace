from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app.extensions import db
from app.models.user import User

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        remember = bool(request.form.get("remember"))

        user = User.query.filter_by(username=username, is_active=True).first()

        if user and user.check_password(password):
            user.last_login = datetime.utcnow()
            db.session.commit()
            login_user(user, remember=remember)
            next_page = request.args.get("next")
            return redirect(next_page or url_for("dashboard.index"))

        flash("Неверный логин или пароль.", "error")

    return render_template("auth/login.html")


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login"))

@auth_bp.route("/change-password", methods=["GET", "POST"])
@login_required
def change_password():
    if request.method == "POST":
        old = request.form.get("old_password", "")
        new = request.form.get("new_password", "").strip()
        confirm = request.form.get("confirm_password", "").strip()

        if not current_user.check_password(old):
            flash("Неверный текущий пароль.", "error")
            return render_template("auth/change_password.html")
        if len(new) < 6:
            flash("Новый пароль должен быть не менее 6 символов.", "error")
            return render_template("auth/change_password.html")
        if new != confirm:
            flash("Пароли не совпадают.", "error")
            return render_template("auth/change_password.html")

        current_user.set_password(new)
        db.session.commit()
        flash("Пароль успешно изменён.", "success")
        return redirect(url_for("dashboard.index"))

    return render_template("auth/change_password.html")