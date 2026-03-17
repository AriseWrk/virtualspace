import os
import uuid
from datetime import datetime
from flask import (Blueprint, render_template, redirect, url_for,
                   flash, request, send_from_directory)
from flask_login import login_required, current_user
from sqlalchemy import func

from app.extensions import db
from app.models.service_task import ServiceTask, ServiceTaskEngineer, ServiceTaskReport
from app.models.pts import ServiceObject
from app.models.user import User

service_bp = Blueprint("service", __name__, url_prefix="/service")

UPLOAD_FOLDER = os.path.join("app", "static", "uploads", "service_tasks")
ALLOWED_EXTS  = {"pdf", "doc", "docx", "jpg", "jpeg", "png", "zip"}


# ─────────────────────────────────────────────────────────────────────────────
# Хелперы доступа
# ─────────────────────────────────────────────────────────────────────────────

def _can_create():
    return current_user.role in ("office", "director", "pts")

def _can_fill_report():
    return current_user.role in ("service", "director", "pts")

def _can_manage():
    return current_user.role in ("director",)

def _next_number():
    last = db.session.query(func.max(ServiceTask.number)).filter(
        ServiceTask.number.like("ПЗ-%")
    ).scalar()
    if last:
        try:
            n = int(last.split("-")[-1]) + 1
        except ValueError:
            n = 1
    else:
        n = 1
    return f"ПЗ-{n:04d}"

def _save_file(file, task_id, prefix=""):
    if not file or file.filename == "":
        return None, None
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in ALLOWED_EXTS:
        return None, None
    folder = os.path.join(UPLOAD_FOLDER, str(task_id))
    os.makedirs(folder, exist_ok=True)
    filename = f"{prefix}{uuid.uuid4().hex}.{ext}"
    file.save(os.path.join(folder, filename))
    return filename, file.filename


# ─────────────────────────────────────────────────────────────────────────────
# ДАШБОРД
# ─────────────────────────────────────────────────────────────────────────────

@service_bp.route("/")
@login_required
def dashboard():
    role = current_user.role

    # Фильтр по роли
    if role == "engineer":
        # Инженер видит только свои задания
        task_ids = db.session.query(ServiceTaskEngineer.task_id).filter_by(
            engineer_id=current_user.id
        ).subquery()
        base_query = ServiceTask.query.filter(ServiceTask.id.in_(task_ids))
    elif role in ("service", "pts"):
        base_query = ServiceTask.query
    elif role in ("office", "director"):
        base_query = ServiceTask.query
    else:
        base_query = ServiceTask.query

    status_filter = request.args.get("status", "")
    priority_filter = request.args.get("priority", "")
    q = request.args.get("q", "").strip()

    query = base_query
    if status_filter:
        query = query.filter_by(status=status_filter)
    if priority_filter:
        query = query.filter_by(priority=priority_filter)
    if q:
        query = query.filter(
            db.or_(
                ServiceTask.object_name.ilike(f"%{q}%"),
                ServiceTask.number.ilike(f"%{q}%"),
            )
        )

    tasks = query.order_by(
        ServiceTask.priority.desc(),
        ServiceTask.planned_date.asc(),
        ServiceTask.created_at.desc()
    ).all()

    # Метрики
    all_tasks = base_query.all()
    stats = {
        "total":       len(all_tasks),
        "new":         sum(1 for t in all_tasks if t.status == "new"),
        "in_progress": sum(1 for t in all_tasks if t.status in ("assigned", "in_progress")),
        "done":        sum(1 for t in all_tasks if t.status == "done"),
        "urgent":      sum(1 for t in all_tasks if t.is_urgent and t.status not in ("done","cancelled","failed")),
    }

    return render_template(
        "service/dashboard.html",
        tasks=tasks,
        stats=stats,
        status_filter=status_filter,
        priority_filter=priority_filter,
        q=q,
        status_choices=ServiceTask.STATUS_CHOICES,
        can_create=_can_create(),
    )


# ─────────────────────────────────────────────────────────────────────────────
# СОЗДАНИЕ ПЛАН-ЗАДАНИЯ (офис)
# ─────────────────────────────────────────────────────────────────────────────

@service_bp.route("/create", methods=["GET", "POST"])
@login_required
def create_task():
    if not _can_create():
        flash("Доступ запрещён.", "error")
        return redirect(url_for("service.dashboard"))

    service_objects = ServiceObject.query.order_by(ServiceObject.name).all()
    engineers = User.query.filter(
        User.role.in_(["engineer", "director"]),
        User.is_active == True
    ).order_by(User.full_name).all()

    if request.method == "POST":
        work_type   = request.form.get("work_type", "to")
        priority    = request.form.get("priority", "normal")
        description = request.form.get("description", "").strip() or None
        engineer_ids = request.form.getlist("engineer_ids")

        planned_date = None
        raw = request.form.get("planned_date", "").strip()
        if raw:
            for fmt in ("%Y-%m-%dT%H:%M", "%Y-%m-%d"):
                try:
                    planned_date = datetime.strptime(raw, fmt)
                    break
                except ValueError:
                    pass

        # Собираем список объектов для создания
        objects_to_create = []  # [(object_id_or_None, name, address), ...]

        # Вариант 1 — из списка ПТС (мультичекбоксы)
        object_ids = request.form.getlist("object_ids[]")
        for oid in object_ids:
            if oid:
                obj = ServiceObject.query.get(int(oid))
                if obj:
                    objects_to_create.append((obj.id, obj.name, obj.address))

        # Вариант 2 — вручную
        manual_names     = request.form.getlist("manual_names[]")
        manual_addresses = request.form.getlist("manual_addresses[]")
        for name, addr in zip(manual_names, manual_addresses):
            name = name.strip()
            if name:
                objects_to_create.append((None, name, addr.strip() or None))

        if not objects_to_create:
            flash("Укажите хотя бы один объект.", "error")
            return render_template("service/task_form.html",
                                   task=None, service_objects=service_objects,
                                   engineers=engineers)

        # Файл — один на все задания
        file = request.files.get("attachment")

        created = []
        for obj_id, obj_name, obj_addr in objects_to_create:
            task = ServiceTask(
                number=_next_number(),
                object_id=obj_id,
                object_name=obj_name,
                object_address=obj_addr,
                work_type=work_type,
                priority=priority,
                status="new",
                planned_date=planned_date,
                description=description,
                created_by_id=current_user.id,
            )
            db.session.add(task)
            db.session.flush()

            for eid in engineer_ids:
                if eid:
                    db.session.add(ServiceTaskEngineer(
                        task_id=task.id, engineer_id=int(eid)
                    ))
            if engineer_ids:
                task.status = "assigned"

            # Файл сохраняем для каждого задания
            filename, orig_name = _save_file(file, task.id)
            if filename:
                task.attachment = filename
                task.attachment_name = orig_name

            created.append(task.number)

        db.session.commit()

        if len(created) == 1:
            flash(f"Задание {created[0]} создано.", "success")
        else:
            flash(f"Создано {len(created)} заданий: {', '.join(created)}.", "success")

        return redirect(url_for("service.dashboard"))

    return render_template("service/task_form.html",
                           task=None, service_objects=service_objects, engineers=engineers)


# ─────────────────────────────────────────────────────────────────────────────
# СТРАНИЦА ПЛАН-ЗАДАНИЯ
# ─────────────────────────────────────────────────────────────────────────────

@service_bp.route("/<int:task_id>")
@login_required
def task_detail(task_id):
    task = ServiceTask.query.get_or_404(task_id)
    engineers = User.query.filter(
        User.role.in_(["engineer", "director"]), User.is_active == True
    ).order_by(User.full_name).all()

    return render_template(
        "service/task_detail.html",
        task=task,
        engineers=engineers,
        can_create=_can_create(),
        can_fill_report=_can_fill_report(),
        can_manage=_can_manage(),
        verdict_choices=ServiceTaskReport.VERDICT_CHOICES,
    )


# ─────────────────────────────────────────────────────────────────────────────
# РЕДАКТИРОВАНИЕ (офис/директор)
# ─────────────────────────────────────────────────────────────────────────────

@service_bp.route("/<int:task_id>/edit", methods=["GET", "POST"])
@login_required
def edit_task(task_id):
    if not _can_create():
        flash("Доступ запрещён.", "error")
        return redirect(url_for("service.task_detail", task_id=task_id))

    task = ServiceTask.query.get_or_404(task_id)
    if task.status in ("done", "failed", "cancelled"):
        flash("Нельзя редактировать завершённое задание.", "warning")
        return redirect(url_for("service.task_detail", task_id=task_id))

    service_objects = ServiceObject.query.order_by(ServiceObject.name).all()
    engineers = User.query.filter(
        User.role.in_(["engineer", "director"]), User.is_active == True
    ).order_by(User.full_name).all()

    if request.method == "POST":
        object_id = request.form.get("object_id", type=int) or None
        if object_id:
            obj = ServiceObject.query.get(object_id)
            task.object_name = obj.name if obj else request.form.get("object_name", task.object_name)
            task.object_address = obj.address if obj else request.form.get("object_address", "").strip() or None
        else:
            task.object_name = request.form.get("object_name", "").strip() or task.object_name
            task.object_address = request.form.get("object_address", "").strip() or None
        task.object_id = object_id

        task.work_type = request.form.get("work_type", task.work_type)
        task.priority  = request.form.get("priority", task.priority)
        task.description = request.form.get("description", "").strip() or None

        raw = request.form.get("planned_date", "").strip()
        if raw:
            try:
                task.planned_date = datetime.strptime(raw, "%Y-%m-%dT%H:%M")
            except ValueError:
                try:
                    task.planned_date = datetime.strptime(raw, "%Y-%m-%d")
                except ValueError:
                    pass

        # Пересобираем инженеров
        ServiceTaskEngineer.query.filter_by(task_id=task.id).delete()
        engineer_ids = request.form.getlist("engineer_ids")
        for eid in engineer_ids:
            if eid:
                db.session.add(ServiceTaskEngineer(task_id=task.id, engineer_id=int(eid)))
        task.status = "assigned" if engineer_ids else "new"

        # Новый файл
        file = request.files.get("attachment")
        filename, orig_name = _save_file(file, task.id)
        if filename:
            task.attachment = filename
            task.attachment_name = orig_name

        task.updated_at = datetime.utcnow()
        db.session.commit()
        flash("Задание обновлено.", "success")
        return redirect(url_for("service.task_detail", task_id=task.id))

    return render_template("service/task_form.html",
                           task=task, service_objects=service_objects, engineers=engineers)


# ─────────────────────────────────────────────────────────────────────────────
# СМЕНА СТАТУСА (офис/директор)
# ─────────────────────────────────────────────────────────────────────────────

@service_bp.route("/<int:task_id>/status", methods=["POST"])
@login_required
def update_status(task_id):
    if not _can_create():
        flash("Доступ запрещён.", "error")
        return redirect(url_for("service.task_detail", task_id=task_id))
    task = ServiceTask.query.get_or_404(task_id)
    new_status = request.form.get("status")
    if new_status in ServiceTask.STATUS_CHOICES:
        task.status = new_status
        task.updated_at = datetime.utcnow()
        db.session.commit()
        flash("Статус обновлён.", "success")
    return redirect(url_for("service.task_detail", task_id=task_id))


# ─────────────────────────────────────────────────────────────────────────────
# ОТЧЁТ СЕРВИСНОЙ СЛУЖБЫ
# ─────────────────────────────────────────────────────────────────────────────

@service_bp.route("/<int:task_id>/report", methods=["POST"])
@login_required
def fill_report(task_id):
    if not _can_fill_report():
        flash("Только сервисная служба может заполнять отчёт.", "error")
        return redirect(url_for("service.task_detail", task_id=task_id))

    task = ServiceTask.query.get_or_404(task_id)

    def parse_dt(field):
        raw = request.form.get(field, "").strip()
        if not raw:
            return None
        for fmt in ("%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M"):
            try:
                return datetime.strptime(raw, fmt)
            except ValueError:
                pass
        return None

    report = task.report or ServiceTaskReport(task_id=task.id)
    report.arrived_at  = parse_dt("arrived_at")
    report.departed_at = parse_dt("departed_at")
    report.verdict     = request.form.get("verdict") or None
    report.notes       = request.form.get("notes", "").strip() or None
    report.filled_by_id = current_user.id
    report.filled_at    = datetime.utcnow()

    # Файл от сервиса
    file = request.files.get("attachment")
    filename, orig_name = _save_file(file, task.id, prefix="report_")
    if filename:
        report.attachment      = filename
        report.attachment_name = orig_name

    if not task.report:
        db.session.add(report)

    # Автообновление статуса задания по вердикту
    verdict = report.verdict
    if verdict == "done":
        task.status = "done"
    elif verdict == "failed":
        task.status = "failed"
    elif verdict in ("partial", "rescheduled"):
        task.status = "in_progress"

    task.updated_at = datetime.utcnow()
    db.session.commit()
    flash("Отчёт сохранён.", "success")
    return redirect(url_for("service.task_detail", task_id=task_id))


# ─────────────────────────────────────────────────────────────────────────────
# СКАЧАТЬ ВЛОЖЕНИЕ
# ─────────────────────────────────────────────────────────────────────────────

@service_bp.route("/<int:task_id>/attachment")
@login_required
def download_attachment(task_id):
    task = ServiceTask.query.get_or_404(task_id)
    if not task.attachment:
        flash("Файл не найден.", "error")
        return redirect(url_for("service.task_detail", task_id=task_id))
    folder = os.path.join(UPLOAD_FOLDER, str(task_id))
    return send_from_directory(folder, task.attachment,
                               as_attachment=True, download_name=task.attachment_name)


@service_bp.route("/<int:task_id>/report/attachment")
@login_required
def download_report_attachment(task_id):
    task = ServiceTask.query.get_or_404(task_id)
    if not task.report or not task.report.attachment:
        flash("Файл не найден.", "error")
        return redirect(url_for("service.task_detail", task_id=task_id))
    folder = os.path.join(UPLOAD_FOLDER, str(task_id))
    return send_from_directory(folder, task.report.attachment,
                               as_attachment=True, download_name=task.report.attachment_name)


# ─────────────────────────────────────────────────────────────────────────────
# СПИСОК ИНЖЕНЕРОВ (для привязки)
# ─────────────────────────────────────────────────────────────────────────────

@service_bp.route("/engineers")
@login_required
def engineers_list():
    if current_user.role not in ("office", "director", "service", "pts"):
        flash("Доступ запрещён.", "error")
        return redirect(url_for("service.dashboard"))

    engineers = User.query.filter(
        User.role.in_(["engineer", "director"]),
        User.is_active == True
    ).order_by(User.full_name).all()

    # Статистика по каждому инженеру
    engineer_stats = []
    for eng in engineers:
        task_ids = db.session.query(ServiceTaskEngineer.task_id).filter_by(
            engineer_id=eng.id
        ).subquery()
        tasks = ServiceTask.query.filter(ServiceTask.id.in_(task_ids)).all()
        engineer_stats.append({
            "user": eng,
            "total":   len(tasks),
            "active":  sum(1 for t in tasks if t.status in ("assigned", "in_progress", "new")),
            "done":    sum(1 for t in tasks if t.status == "done"),
        })

    return render_template("service/engineers.html",
                           engineer_stats=engineer_stats,
                           can_create=_can_create())