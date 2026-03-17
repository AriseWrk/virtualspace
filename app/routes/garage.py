from datetime import datetime, date
from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.extensions import db
from app.models.vehicle import Vehicle, VehicleTrip, VehicleRequest
from app.models.user import User

garage_bp = Blueprint("garage", __name__, url_prefix="/garage")


def garage_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if current_user.role not in ("garage", "director"):
            flash("Доступ только для зав. гаража и директора.", "error")
            return redirect(url_for("garage.dashboard"))
        return f(*args, **kwargs)
    return login_required(decorated)


def _parse_date(val):
    if not val:
        return None
    for fmt in ("%Y-%m-%d",):
        try:
            return datetime.strptime(val.strip(), fmt).date()
        except ValueError:
            pass
    return None


# ─────────────────────────────────────────────────────────────────────────────
# ДАШБОРД
# ─────────────────────────────────────────────────────────────────────────────

@garage_bp.route("/")
@login_required
def dashboard():
    vehicles = Vehicle.query.order_by(Vehicle.name).all()

    # Предупреждения — документы истекают через 30 дней
    warnings = []
    today = date.today()
    for v in vehicles:
        if v.insurance_days_left is not None and v.insurance_days_left <= 30:
            warnings.append({
                "vehicle": v,
                "type": "ОСАГО",
                "days": v.insurance_days_left,
                "date": v.insurance_date,
            })
        if v.inspection_days_left is not None and v.inspection_days_left <= 30:
            warnings.append({
                "vehicle": v,
                "type": "Техосмотр",
                "days": v.inspection_days_left,
                "date": v.inspection_date,
            })
        if v.sto_days_left is not None and v.sto_days_left <= 30:
            warnings.append({
                "vehicle": v,
                "type": "ТО",
                "days": v.sto_days_left,
                "date": v.sto_next_date,
            })

    # Новые заявки
    new_requests = VehicleRequest.query.filter_by(status="new").count()

    stats = {
        "total":       len(vehicles),
        "available":   sum(1 for v in vehicles if v.status == "available"),
        "on_route":    sum(1 for v in vehicles if v.status == "on_route"),
        "maintenance": sum(1 for v in vehicles if v.status == "maintenance"),
        "new_requests": new_requests,
    }

    return render_template(
        "garage/dashboard.html",
        vehicles=vehicles,
        warnings=warnings,
        stats=stats,
    )


# ─────────────────────────────────────────────────────────────────────────────
# СПИСОК ТРАНСПОРТА
# ─────────────────────────────────────────────────────────────────────────────

@garage_bp.route("/vehicles")
@login_required
def vehicles():
    status_filter = request.args.get("status", "")
    query = Vehicle.query
    if status_filter:
        query = query.filter_by(status=status_filter)
    all_vehicles = query.order_by(Vehicle.name).all()
    drivers = User.query.filter(User.is_active == True).order_by(User.full_name).all()
    return render_template(
        "garage/vehicles.html",
        vehicles=all_vehicles,
        status_filter=status_filter,
        status_choices=Vehicle.STATUS_CHOICES,
        drivers=drivers,
    )


# ─────────────────────────────────────────────────────────────────────────────
# ДОБАВИТЬ / РЕДАКТИРОВАТЬ ТРАНСПОРТ
# ─────────────────────────────────────────────────────────────────────────────

@garage_bp.route("/vehicles/add", methods=["GET", "POST"])
@garage_required
def add_vehicle():
    drivers = User.query.filter(User.is_active == True).order_by(User.full_name).all()
    if request.method == "POST":
        plate = request.form.get("plate", "").strip().upper()
        if Vehicle.query.filter_by(plate=plate).first():
            flash(f"Автомобиль с номером {plate} уже существует.", "error")
            return render_template("garage/vehicle_form.html", vehicle=None, drivers=drivers)

        v = Vehicle(
            name=request.form["name"].strip(),
            plate=plate,
            year=request.form.get("year", type=int) or None,
            color=request.form.get("color", "").strip() or None,
            status=request.form.get("status", "available"),
            mileage=request.form.get("mileage", 0, type=int),
            driver_id=request.form.get("driver_id", type=int) or None,
            sto_date=_parse_date(request.form.get("sto_date")),
            sto_next_date=_parse_date(request.form.get("sto_next_date")),
            insurance_date=_parse_date(request.form.get("insurance_date")),
            inspection_date=_parse_date(request.form.get("inspection_date")),
            notes=request.form.get("notes", "").strip() or None,
        )
        db.session.add(v)
        db.session.commit()
        flash(f"Автомобиль «{v.name}» добавлен.", "success")
        return redirect(url_for("garage.vehicles"))
    return render_template("garage/vehicle_form.html", vehicle=None, drivers=drivers)


@garage_bp.route("/vehicles/<int:vid>/edit", methods=["GET", "POST"])
@garage_required
def edit_vehicle(vid):
    v = Vehicle.query.get_or_404(vid)
    drivers = User.query.filter(User.is_active == True).order_by(User.full_name).all()
    if request.method == "POST":
        v.name            = request.form["name"].strip()
        v.plate           = request.form.get("plate", "").strip().upper()
        v.year            = request.form.get("year", type=int) or None
        v.color           = request.form.get("color", "").strip() or None
        v.status          = request.form.get("status", v.status)
        v.mileage         = request.form.get("mileage", v.mileage, type=int)
        v.driver_id       = request.form.get("driver_id", type=int) or None
        v.sto_date        = _parse_date(request.form.get("sto_date"))
        v.sto_next_date   = _parse_date(request.form.get("sto_next_date"))
        v.insurance_date  = _parse_date(request.form.get("insurance_date"))
        v.inspection_date = _parse_date(request.form.get("inspection_date"))
        v.notes           = request.form.get("notes", "").strip() or None
        v.updated_at      = datetime.utcnow()
        db.session.commit()
        flash(f"Автомобиль «{v.name}» обновлён.", "success")
        return redirect(url_for("garage.vehicles"))
    return render_template("garage/vehicle_form.html", vehicle=v, drivers=drivers)


@garage_bp.route("/vehicles/<int:vid>/delete", methods=["POST"])
@garage_required
def delete_vehicle(vid):
    v = Vehicle.query.get_or_404(vid)
    db.session.delete(v)
    db.session.commit()
    flash(f"Автомобиль «{v.name}» удалён.", "success")
    return redirect(url_for("garage.vehicles"))


@garage_bp.route("/vehicles/<int:vid>/status", methods=["POST"])
@garage_required
def update_vehicle_status(vid):
    v = Vehicle.query.get_or_404(vid)
    new_status = request.form.get("status")
    if new_status in Vehicle.STATUS_CHOICES:
        v.status = new_status
        db.session.commit()
        flash(f"Статус «{v.name}» обновлён.", "success")
    return redirect(url_for("garage.vehicles"))


# ─────────────────────────────────────────────────────────────────────────────
# ЖУРНАЛ ПОЕЗДОК
# ─────────────────────────────────────────────────────────────────────────────

@garage_bp.route("/vehicles/<int:vid>")
@login_required
def vehicle_detail(vid):
    v = Vehicle.query.get_or_404(vid)
    drivers = User.query.filter(User.is_active == True).order_by(User.full_name).all()
    trips = v.trips.limit(50).all()
    return render_template(
        "garage/vehicle_detail.html",
        vehicle=v,
        trips=trips,
        drivers=drivers,
        today=date.today().isoformat(),
        can_manage=current_user.role in ("garage", "director"),
    )


@garage_bp.route("/vehicles/<int:vid>/trips/add", methods=["POST"])
@garage_required
def add_trip(vid):
    v = Vehicle.query.get_or_404(vid)
    mileage_end = request.form.get("mileage_end", type=int)

    trip = VehicleTrip(
        vehicle_id=vid,
        driver_id=request.form.get("driver_id", type=int) or v.driver_id,
        date=_parse_date(request.form.get("trip_date")) or date.today(),
        destination=request.form["destination"].strip(),
        purpose=request.form.get("purpose", "").strip() or None,
        passengers=request.form.get("passengers", "").strip() or None,
        mileage_start=request.form.get("mileage_start", type=int) or v.mileage,
        mileage_end=mileage_end,
        notes=request.form.get("notes", "").strip() or None,
    )
    db.session.add(trip)

    # Обновляем пробег авто
    if mileage_end and mileage_end > v.mileage:
        v.mileage = mileage_end

    db.session.commit()
    flash("Поездка добавлена.", "success")
    return redirect(url_for("garage.vehicle_detail", vid=vid))


@garage_bp.route("/trips/<int:trip_id>/delete", methods=["POST"])
@garage_required
def delete_trip(trip_id):
    trip = VehicleTrip.query.get_or_404(trip_id)
    vid = trip.vehicle_id
    db.session.delete(trip)
    db.session.commit()
    flash("Запись удалена.", "success")
    return redirect(url_for("garage.vehicle_detail", vid=vid))


# ─────────────────────────────────────────────────────────────────────────────
# ЗАЯВКИ НА ТРАНСПОРТ
# ─────────────────────────────────────────────────────────────────────────────

@garage_bp.route("/requests")
@login_required
def requests_list():
    role = current_user.role
    if role in ("garage", "director"):
        reqs = VehicleRequest.query.order_by(
            VehicleRequest.status,
            VehicleRequest.planned_date
        ).all()
    else:
        reqs = VehicleRequest.query.filter_by(
            requester_id=current_user.id
        ).order_by(VehicleRequest.created_at.desc()).all()

    return render_template(
        "garage/requests.html",
        requests=reqs,
        can_manage=role in ("garage", "director"),
        vehicles_list=Vehicle.query.filter_by(status="available").order_by(Vehicle.name).all(),
    )


@garage_bp.route("/request", methods=["GET", "POST"])
@login_required
def transport_request():
    vehicles = Vehicle.query.filter_by(status="available").order_by(Vehicle.name).all()
    if request.method == "POST":
        req = VehicleRequest(
            vehicle_id=request.form.get("vehicle_id", type=int) or None,
            requester_id=current_user.id,
            status="new",
            planned_date=_parse_date(request.form["planned_date"]) or date.today(),
            destination=request.form["destination"].strip(),
            purpose=request.form.get("purpose", "").strip() or None,
            passengers=request.form.get("passengers", 1, type=int),
            notes=request.form.get("notes", "").strip() or None,
        )
        db.session.add(req)
        db.session.commit()
        flash("Заявка подана. Ожидайте подтверждения.", "success")
        return redirect(url_for("garage.requests_list"))
    return render_template("garage/request.html", vehicles=vehicles,
                           today=date.today().isoformat())


@garage_bp.route("/requests/<int:req_id>/review", methods=["POST"])
@garage_required
def review_request(req_id):
    req = VehicleRequest.query.get_or_404(req_id)
    action = request.form.get("action")
    req.status = "approved" if action == "approve" else "rejected"
    req.vehicle_id = request.form.get("vehicle_id", type=int) or req.vehicle_id
    req.review_note = request.form.get("review_note", "").strip() or None
    req.reviewed_by_id = current_user.id
    db.session.commit()
    flash(f"Заявка {'одобрена' if req.status == 'approved' else 'отклонена'}.", "success")
    return redirect(url_for("garage.requests_list"))