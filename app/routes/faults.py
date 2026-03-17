from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.extensions import db
from app.models.fault_record import FaultRecord

faults_bp = Blueprint("faults", __name__, url_prefix="/faults")


@faults_bp.route("/")
@login_required
def index():
    q        = request.args.get("q", "").strip()
    category = request.args.get("cat", "")
    my_only  = request.args.get("my", type=int)

    query = FaultRecord.query.filter(
        db.or_(FaultRecord.is_public == True,
               FaultRecord.author_id == current_user.id)
    )
    if category:
        query = query.filter_by(category=category)
    if my_only:
        query = query.filter_by(author_id=current_user.id)
    if q:
        query = query.filter(
            db.or_(
                FaultRecord.title.ilike(f"%{q}%"),
                FaultRecord.symptoms.ilike(f"%{q}%"),
                FaultRecord.tags.ilike(f"%{q}%"),
                FaultRecord.equipment.ilike(f"%{q}%"),
            )
        )

    records = query.order_by(FaultRecord.created_at.desc()).all()
    return render_template(
        "faults/index.html",
        records=records,
        q=q,
        category=category,
        my_only=my_only,
        categories=FaultRecord.CATEGORIES,
    )


@faults_bp.route("/new", methods=["GET", "POST"])
@login_required
def create():
    if request.method == "POST":
        rec = FaultRecord(
            title=request.form["title"].strip(),
            category=request.form.get("category", "other"),
            symptoms=request.form["symptoms"].strip(),
            solution=request.form["solution"].strip(),
            equipment=request.form.get("equipment", "").strip() or None,
            tags=request.form.get("tags", "").strip() or None,
            is_public="is_public" in request.form,
            author_id=current_user.id,
        )
        db.session.add(rec)
        db.session.commit()
        flash("Запись добавлена в базу.", "success")
        return redirect(url_for("faults.detail", rec_id=rec.id))
    return render_template("faults/form.html", record=None,
                           categories=FaultRecord.CATEGORIES)


@faults_bp.route("/<int:rec_id>")
@login_required
def detail(rec_id):
    rec = FaultRecord.query.get_or_404(rec_id)
    if not rec.is_public and rec.author_id != current_user.id:
        flash("Запись недоступна.", "error")
        return redirect(url_for("faults.index"))
    rec.views += 1
    db.session.commit()
    return render_template("faults/detail.html", record=rec)


@faults_bp.route("/<int:rec_id>/edit", methods=["GET", "POST"])
@login_required
def edit(rec_id):
    rec = FaultRecord.query.get_or_404(rec_id)
    if rec.author_id != current_user.id and current_user.role != "director":
        flash("Только автор может редактировать.", "error")
        return redirect(url_for("faults.detail", rec_id=rec_id))
    if request.method == "POST":
        rec.title     = request.form["title"].strip()
        rec.category  = request.form.get("category", rec.category)
        rec.symptoms  = request.form["symptoms"].strip()
        rec.solution  = request.form["solution"].strip()
        rec.equipment = request.form.get("equipment", "").strip() or None
        rec.tags      = request.form.get("tags", "").strip() or None
        rec.is_public = "is_public" in request.form
        rec.updated_at = datetime.utcnow()
        db.session.commit()
        flash("Запись обновлена.", "success")
        return redirect(url_for("faults.detail", rec_id=rec_id))
    return render_template("faults/form.html", record=rec,
                           categories=FaultRecord.CATEGORIES)


@faults_bp.route("/<int:rec_id>/delete", methods=["POST"])
@login_required
def delete(rec_id):
    rec = FaultRecord.query.get_or_404(rec_id)
    if rec.author_id != current_user.id and current_user.role != "director":
        flash("Только автор может удалить.", "error")
        return redirect(url_for("faults.detail", rec_id=rec_id))
    db.session.delete(rec)
    db.session.commit()
    flash("Запись удалена.", "success")
    return redirect(url_for("faults.index"))