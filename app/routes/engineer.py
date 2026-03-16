import os
import uuid
from datetime import datetime
from flask import (Blueprint, render_template, redirect,
                   url_for, flash, request, abort)
from flask_login import login_required, current_user
from app.extensions import db
from app.models.order import Order
from app.models.project import (Project, ChecklistItem, CableJournal,
                                 IPTable, ProjectPhoto, ProjectNote)
from app.models.user import User
from functools import wraps

engineer_bp = Blueprint("engineer", __name__, url_prefix="/engineer")

UPLOAD_FOLDER = os.path.join("app", "static", "uploads", "projects")


def engineer_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if current_user.role not in ("engineer", "director"):
            flash("Доступ запрещён.", "error")
            return redirect(url_for("dashboard.index"))
        return f(*args, **kwargs)
    return login_required(decorated)


# ===== ДАШБОРД =====

@engineer_bp.route("/")
@engineer_required
def dashboard():
    if current_user.role == "director":
        my_projects = Project.query.order_by(Project.updated_at.desc()).limit(5).all()
        open_orders = Order.query.filter(Order.status.in_(["new", "in_progress"])).count()
        total_orders = Order.query.count()
    else:
        my_projects = Project.query.filter_by(
            engineer_id=current_user.id
        ).order_by(Project.updated_at.desc()).limit(5).all()
        open_orders = Order.query.filter(
            Order.assigned_to_id == current_user.id,
            Order.status.in_(["new", "in_progress"])
        ).count()
        total_orders = Order.query.filter_by(assigned_to_id=current_user.id).count()

    stats = {
        "open_orders": open_orders,
        "total_orders": total_orders,
        "active_projects": Project.query.filter_by(
            status="in_progress",
            **({"engineer_id": current_user.id} if current_user.role != "director" else {})
        ).count(),
    }
    return render_template("engineer/dashboard.html", stats=stats, my_projects=my_projects)


# ===== ПРОЕКТЫ — СПИСОК =====

@engineer_bp.route("/projects")
@engineer_required
def projects():
    status_filter = request.args.get("status", "")
    if current_user.role == "director":
        query = Project.query
    else:
        query = Project.query.filter_by(engineer_id=current_user.id)

    if status_filter:
        query = query.filter_by(status=status_filter)

    all_projects = query.order_by(Project.updated_at.desc()).all()
    engineers = User.query.filter(User.role.in_(["engineer", "director"])).all()
    return render_template("engineer/projects.html",
                           projects=all_projects,
                           status_filter=status_filter,
                           engineers=engineers)


@engineer_bp.route("/projects/create", methods=["GET", "POST"])
@engineer_required
def create_project():
    engineers = User.query.filter(User.role.in_(["engineer", "director"])).all()
    if request.method == "POST":
        project = Project(
            name=request.form["name"].strip(),
            address=request.form.get("address", "").strip() or None,
            client=request.form.get("client", "").strip() or None,
            description=request.form.get("description", "").strip() or None,
            status=request.form.get("status", "planning"),
            engineer_id=int(request.form.get("engineer_id", current_user.id)),
        )
        db.session.add(project)
        db.session.flush()

        # Добавляем стандартный чеклист
        default_checklist = [
            ("Выезд на объект, обследование", "preparation", 1),
            ("Согласование схемы размещения", "preparation", 2),
            ("Получение материалов со склада", "preparation", 3),
            ("Прокладка кабельных трасс", "cabling", 4),
            ("Монтаж оборудования", "installation", 5),
            ("Подключение кабелей", "cabling", 6),
            ("Пуско-наладочные работы", "commissioning", 7),
            ("Тестирование системы", "commissioning", 8),
            ("Оформление кабельного журнала", "documentation", 9),
            ("Оформление исполнительной документации", "documentation", 10),
            ("Сдача объекта заказчику", "handover", 11),
        ]
        for title, category, order in default_checklist:
            item = ChecklistItem(
                project_id=project.id,
                title=title,
                category=category,
                order=order,
            )
            db.session.add(item)

        db.session.commit()
        flash(f"Проект «{project.name}» создан.", "success")
        return redirect(url_for("engineer.project_detail", project_id=project.id))

    return render_template("engineer/project_form.html", project=None, engineers=engineers)


# ===== СТРАНИЦА ОБЪЕКТА =====

@engineer_bp.route("/projects/<int:project_id>")
@engineer_required
def project_detail(project_id):
    project = Project.query.get_or_404(project_id)
    if current_user.role not in ("director",) and project.engineer_id != current_user.id:
        abort(403)

    # Заказы склада привязанные к этому объекту (по названию)
    related_orders = Order.query.filter(
        Order.object_name.ilike(f"%{project.name}%")
    ).order_by(Order.created_at.desc()).all()

    # Группируем чеклист по категориям
    checklist_by_category = {}
    for item in project.checklist:
        cat = item.category_label
        if cat not in checklist_by_category:
            checklist_by_category[cat] = []
        checklist_by_category[cat].append(item)

    return render_template(
        "engineer/project_detail.html",
        project=project,
        related_orders=related_orders,
        checklist_by_category=checklist_by_category,
    )


@engineer_bp.route("/projects/<int:project_id>/edit", methods=["GET", "POST"])
@engineer_required
def edit_project(project_id):
    project = Project.query.get_or_404(project_id)
    engineers = User.query.filter(User.role.in_(["engineer", "director"])).all()
    if request.method == "POST":
        project.name        = request.form["name"].strip()
        project.address     = request.form.get("address", "").strip() or None
        project.client      = request.form.get("client", "").strip() or None
        project.description = request.form.get("description", "").strip() or None
        project.status      = request.form.get("status", "planning")
        project.engineer_id = int(request.form.get("engineer_id", project.engineer_id))
        project.updated_at  = datetime.utcnow()
        db.session.commit()
        flash("Проект обновлён.", "success")
        return redirect(url_for("engineer.project_detail", project_id=project.id))
    return render_template("engineer/project_form.html", project=project, engineers=engineers)


# ===== ЧЕКЛИСТ =====

@engineer_bp.route("/projects/<int:project_id>/checklist/toggle/<int:item_id>", methods=["POST"])
@engineer_required
def toggle_checklist(project_id, item_id):
    item = ChecklistItem.query.get_or_404(item_id)
    item.is_done = not item.is_done
    item.done_at = datetime.utcnow() if item.is_done else None
    item.done_by_id = current_user.id if item.is_done else None
    db.session.commit()
    return redirect(url_for("engineer.project_detail", project_id=project_id) + "#checklist")


@engineer_bp.route("/projects/<int:project_id>/checklist/add", methods=["POST"])
@engineer_required
def add_checklist_item(project_id):
    project = Project.query.get_or_404(project_id)
    title = request.form.get("title", "").strip()
    if title:
        max_order = db.session.query(
            db.func.max(ChecklistItem.order)
        ).filter_by(project_id=project_id).scalar() or 0
        item = ChecklistItem(
            project_id=project_id,
            title=title,
            category=request.form.get("category", "installation"),
            order=max_order + 1,
        )
        db.session.add(item)
        db.session.commit()
        flash("Пункт добавлен.", "success")
    return redirect(url_for("engineer.project_detail", project_id=project_id) + "#checklist")


# ===== КАБЕЛЬНЫЙ ЖУРНАЛ =====

@engineer_bp.route("/projects/<int:project_id>/cable/add", methods=["POST"])
@engineer_required
def add_cable(project_id):
    cable = CableJournal(
        project_id=project_id,
        number=request.form["number"].strip(),
        cable_type=request.form["cable_type"].strip(),
        from_point=request.form["from_point"].strip(),
        to_point=request.form["to_point"].strip(),
        length=float(request.form["length"]) if request.form.get("length") else None,
        section=request.form.get("section", "").strip() or None,
        status=request.form.get("status", "planned"),
        notes=request.form.get("notes", "").strip() or None,
    )
    db.session.add(cable)
    db.session.commit()
    flash("Кабель добавлен в журнал.", "success")
    return redirect(url_for("engineer.project_detail", project_id=project_id) + "#cables")


@engineer_bp.route("/projects/<int:project_id>/cable/<int:cable_id>/status", methods=["POST"])
@engineer_required
def update_cable_status(project_id, cable_id):
    cable = CableJournal.query.get_or_404(cable_id)
    cable.status = request.form.get("status", cable.status)
    db.session.commit()
    return redirect(url_for("engineer.project_detail", project_id=project_id) + "#cables")


@engineer_bp.route("/projects/<int:project_id>/cable/<int:cable_id>/delete", methods=["POST"])
@engineer_required
def delete_cable(project_id, cable_id):
    cable = CableJournal.query.get_or_404(cable_id)
    db.session.delete(cable)
    db.session.commit()
    flash("Запись удалена.", "success")
    return redirect(url_for("engineer.project_detail", project_id=project_id) + "#cables")


# ===== ТАБЛИЦА IP =====

@engineer_bp.route("/projects/<int:project_id>/ip/add", methods=["POST"])
@engineer_required
def add_ip(project_id):
    entry = IPTable(
        project_id=project_id,
        ip_address=request.form["ip_address"].strip(),
        mac_address=request.form.get("mac_address", "").strip() or None,
        device_name=request.form["device_name"].strip(),
        device_model=request.form.get("device_model", "").strip() or None,
        location=request.form.get("location", "").strip() or None,
        login=request.form.get("login", "").strip() or None,
        password=request.form.get("password", "").strip() or None,
        status=request.form.get("status", "active"),
        notes=request.form.get("notes", "").strip() or None,
    )
    db.session.add(entry)
    db.session.commit()
    flash("Устройство добавлено в таблицу IP.", "success")
    return redirect(url_for("engineer.project_detail", project_id=project_id) + "#iptable")


@engineer_bp.route("/projects/<int:project_id>/ip/<int:ip_id>/delete", methods=["POST"])
@engineer_required
def delete_ip(project_id, ip_id):
    entry = IPTable.query.get_or_404(ip_id)
    db.session.delete(entry)
    db.session.commit()
    flash("Запись удалена.", "success")
    return redirect(url_for("engineer.project_detail", project_id=project_id) + "#iptable")


# ===== ФОТО =====

@engineer_bp.route("/projects/<int:project_id>/photo/upload", methods=["POST"])
@engineer_required
def upload_photo(project_id):
    if "photo" not in request.files:
        flash("Файл не выбран.", "error")
        return redirect(url_for("engineer.project_detail", project_id=project_id))

    file = request.files["photo"]
    if file.filename == "":
        flash("Файл не выбран.", "error")
        return redirect(url_for("engineer.project_detail", project_id=project_id))

    allowed = {"jpg", "jpeg", "png", "gif", "webp"}
    ext = file.filename.rsplit(".", 1)[-1].lower()
    if ext not in allowed:
        flash("Разрешены только изображения (jpg, png, gif, webp).", "error")
        return redirect(url_for("engineer.project_detail", project_id=project_id))

    folder = os.path.join(UPLOAD_FOLDER, str(project_id))
    os.makedirs(folder, exist_ok=True)

    filename = f"{uuid.uuid4().hex}.{ext}"
    file.save(os.path.join(folder, filename))

    photo = ProjectPhoto(
        project_id=project_id,
        filename=filename,
        description=request.form.get("description", "").strip() or None,
        uploaded_by=current_user.id,
    )
    db.session.add(photo)
    db.session.commit()
    flash("Фото загружено.", "success")
    return redirect(url_for("engineer.project_detail", project_id=project_id) + "#photos")


@engineer_bp.route("/projects/<int:project_id>/photo/<int:photo_id>/delete", methods=["POST"])
@engineer_required
def delete_photo(project_id, photo_id):
    photo = ProjectPhoto.query.get_or_404(photo_id)
    filepath = os.path.join(UPLOAD_FOLDER, str(project_id), photo.filename)
    if os.path.exists(filepath):
        os.remove(filepath)
    db.session.delete(photo)
    db.session.commit()
    flash("Фото удалено.", "success")
    return redirect(url_for("engineer.project_detail", project_id=project_id) + "#photos")


# ===== ЗАМЕТКИ =====

@engineer_bp.route("/projects/<int:project_id>/note/add", methods=["POST"])
@engineer_required
def add_note(project_id):
    text = request.form.get("text", "").strip()
    if text:
        note = ProjectNote(
            project_id=project_id,
            text=text,
            note_type=request.form.get("note_type", "note"),
            author_id=current_user.id,
        )
        db.session.add(note)
        db.session.commit()
        flash("Заметка добавлена.", "success")
    return redirect(url_for("engineer.project_detail", project_id=project_id) + "#notes")


# ===== ЭКСПОРТ =====

@engineer_bp.route("/projects/<int:project_id>/export")
@engineer_required
def export_project(project_id):
    import io
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment

    project = Project.query.get_or_404(project_id)
    wb = openpyxl.Workbook()

    # ===== Лист 1: Общая информация =====
    ws1 = wb.active
    ws1.title = "Объект"
    ws1.merge_cells("A1:D1")
    ws1["A1"] = f"Объект: {project.name}"
    ws1["A1"].font = Font(bold=True, size=14)
    ws1.append(["Адрес:", project.address or "—"])
    ws1.append(["Заказчик:", project.client or "—"])
    ws1.append(["Статус:", project.status_label])
    ws1.append(["Инженер:", project.engineer.full_name])
    ws1.append(["Прогресс чеклиста:", f"{project.checklist_progress}%"])
    ws1.append(["Создан:", project.created_at.strftime("%d.%m.%Y")])
    ws1.column_dimensions["A"].width = 25
    ws1.column_dimensions["B"].width = 40

    # ===== Лист 2: Чеклист =====
    ws2 = wb.create_sheet("Чеклист")
    ws2.append(["#", "Пункт", "Категория", "Выполнен", "Дата", "Исполнитель"])
    ws2[1][0].font = Font(bold=True)
    for i, item in enumerate(project.checklist, 1):
        ws2.append([
            i, item.title, item.category_label,
            "Да" if item.is_done else "Нет",
            item.done_at.strftime("%d.%m.%Y") if item.done_at else "—",
            item.done_by.full_name if item.done_by else "—",
        ])
    for col, w in zip("ABCDEF", [5, 50, 20, 10, 12, 25]):
        ws2.column_dimensions[col].width = w

    # ===== Лист 3: Кабельный журнал =====
    ws3 = wb.create_sheet("Кабельный журнал")
    ws3.append(["№", "Тип кабеля", "От", "До", "Длина (м)", "Сечение", "Статус", "Примечание"])
    for cell in ws3[1]:
        cell.font = Font(bold=True)
    for c in project.cable_journal:
        ws3.append([
            c.number, c.cable_type, c.from_point, c.to_point,
            c.length or "—", c.section or "—", c.status_label, c.notes or "—",
        ])
    for col, w in zip("ABCDEFGH", [8, 25, 30, 30, 10, 10, 15, 25]):
        ws3.column_dimensions[col].width = w

    # ===== Лист 4: Таблица IP =====
    ws4 = wb.create_sheet("Таблица IP (СОТ)")
    ws4.append(["IP-адрес", "MAC", "Устройство", "Модель", "Расположение", "Статус", "Примечание"])
    for cell in ws4[1]:
        cell.font = Font(bold=True)
    for ip in project.ip_table:
        ws4.append([
            ip.ip_address, ip.mac_address or "—", ip.device_name,
            ip.device_model or "—", ip.location or "—",
            ip.status_label, ip.notes or "—",
        ])
    for col, w in zip("ABCDEFG", [16, 18, 30, 25, 25, 12, 25]):
        ws4.column_dimensions[col].width = w

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    from flask import send_file
    filename = f"project_{project.id}_{datetime.now().strftime('%Y%m%d')}.xlsx"
    return send_file(buf, as_attachment=True, download_name=filename,
                     mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


# ===== ОСТАЛЬНЫЕ РАЗДЕЛЫ =====

@engineer_bp.route("/handbook")
@engineer_required
def handbook():
    return render_template("engineer/handbook.html")


@engineer_bp.route("/tests")
@engineer_required
def tests():
    return render_template("engineer/tests.html")


@engineer_bp.route("/regulations")
@engineer_required
def regulations():
    return render_template("engineer/regulations.html")


@engineer_bp.route("/software")
@engineer_required
def software():
    return render_template("engineer/software.html")


@engineer_bp.route("/equipment")
@engineer_required
def equipment():
    return render_template("engineer/equipment.html")