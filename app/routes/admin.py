from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash
from app.extensions import db
from app.models.user import User
from app.models.warehouse import Category

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if current_user.role != "director":
            flash("Доступ только для директора.", "error")
            return redirect(url_for("dashboard.index"))
        return f(*args, **kwargs)
    return login_required(decorated)


# ========== ПОЛЬЗОВАТЕЛИ ==========

@admin_bp.route("/users")
@admin_required
def users():
    all_users = User.query.order_by(User.full_name).all()
    return render_template("admin/users.html", users=all_users)


@admin_bp.route("/users/create", methods=["GET", "POST"])
@admin_required
def create_user():
    if request.method == "POST":
        username = request.form["username"].strip()
        if User.query.filter_by(username=username).first():
            flash(f"Логин «{username}» уже занят.", "error")
            return render_template("admin/user_form.html", user=None)

        user = User(
            username=username,
            full_name=request.form["full_name"].strip(),
            role=request.form["role"],
            is_active=True,
        )
        user.set_password(request.form["password"])
        db.session.add(user)
        db.session.commit()
        flash(f"Пользователь «{user.full_name}» создан.", "success")
        return redirect(url_for("admin.users"))
    return render_template("admin/user_form.html", user=None)


@admin_bp.route("/users/<int:user_id>/edit", methods=["GET", "POST"])
@admin_required
def edit_user(user_id):
    user = User.query.get_or_404(user_id)
    if request.method == "POST":
        user.full_name = request.form["full_name"].strip()
        user.role = request.form["role"]
        user.is_active = "is_active" in request.form

        new_password = request.form.get("password", "").strip()
        if new_password:
            user.set_password(new_password)
            flash("Пароль изменён.", "success")

        db.session.commit()
        flash(f"Пользователь «{user.full_name}» обновлён.", "success")
        return redirect(url_for("admin.users"))
    return render_template("admin/user_form.html", user=user)


@admin_bp.route("/users/<int:user_id>/toggle", methods=["POST"])
@admin_required
def toggle_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash("Нельзя заблокировать самого себя.", "error")
        return redirect(url_for("admin.users"))
    user.is_active = not user.is_active
    db.session.commit()
    status = "разблокирован" if user.is_active else "заблокирован"
    flash(f"Пользователь «{user.full_name}» {status}.", "success")
    return redirect(url_for("admin.users"))


@admin_bp.route("/users/<int:user_id>/delete", methods=["POST"])
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash("Нельзя удалить самого себя.", "error")
        return redirect(url_for("admin.users"))
    db.session.delete(user)
    db.session.commit()
    flash(f"Пользователь «{user.full_name}» удалён.", "success")
    return redirect(url_for("admin.users"))


# ========== КАТЕГОРИИ СКЛАДА ==========

@admin_bp.route("/categories")
@admin_required
def categories():
    all_cats = Category.query.order_by(Category.name).all()
    return render_template("admin/categories.html", categories=all_cats)


@admin_bp.route("/categories/create", methods=["POST"])
@admin_required
def create_category():
    name = request.form.get("name", "").strip()
    if not name:
        flash("Название не может быть пустым.", "error")
        return redirect(url_for("admin.categories"))
    if Category.query.filter_by(name=name).first():
        flash(f"Категория «{name}» уже существует.", "error")
        return redirect(url_for("admin.categories"))
    cat = Category(name=name, description=request.form.get("description", "").strip() or None)
    db.session.add(cat)
    db.session.commit()
    flash(f"Категория «{name}» добавлена.", "success")
    return redirect(url_for("admin.categories"))


@admin_bp.route("/categories/<int:cat_id>/edit", methods=["POST"])
@admin_required
def edit_category(cat_id):
    cat = Category.query.get_or_404(cat_id)
    cat.name = request.form.get("name", cat.name).strip()
    cat.description = request.form.get("description", "").strip() or None
    db.session.commit()
    flash(f"Категория «{cat.name}» обновлена.", "success")
    return redirect(url_for("admin.categories"))


@admin_bp.route("/categories/<int:cat_id>/delete", methods=["POST"])
@admin_required
def delete_category(cat_id):
    cat = Category.query.get_or_404(cat_id)
    if cat.items.count() > 0:
        flash(f"Нельзя удалить — в категории есть позиции ({cat.items.count()} шт).", "error")
        return redirect(url_for("admin.categories"))
    db.session.delete(cat)
    db.session.commit()
    flash(f"Категория «{cat.name}» удалена.", "success")
    return redirect(url_for("admin.categories"))