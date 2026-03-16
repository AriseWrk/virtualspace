from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.extensions import db

garage_bp = Blueprint("garage", __name__, url_prefix="/garage")


# ===== МОДЕЛИ (добавим в models позже) =====
# Пока используем заглушки данных

@garage_bp.route("/")
@login_required
def dashboard():
    vehicles = [
        {"name": "Lada Largus", "plate": "А123БВ77", "driver": "Сидоров П.А.", "status": "available", "mileage": 87450},
        {"name": "Ford Transit", "plate": "В456ГД77", "driver": "Козлов М.В.", "status": "on_route", "mileage": 124300},
        {"name": "Газель Next", "plate": "Е789ЖЗ77", "driver": "Никитин С.О.", "status": "available", "mileage": 56200},
        {"name": "УАЗ Патриот", "plate": "И012КЛ77", "driver": "—", "status": "maintenance", "mileage": 201000},
    ]
    return render_template("garage/dashboard.html", vehicles=vehicles)


@garage_bp.route("/request", methods=["GET", "POST"])
@login_required
def transport_request():
    if request.method == "POST":
        flash("Заявка на транспорт подана. Ожидайте подтверждения.", "success")
        return redirect(url_for("garage.dashboard"))
    return render_template("garage/request.html")


@garage_bp.route("/vehicles")
@login_required
def vehicles():
    return render_template("garage/vehicles.html")