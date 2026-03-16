import io
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file
from flask_login import login_required, current_user
from app.extensions import db
from app.models.warehouse import Item, Category
from app.models.order import Order, OrderItem
from app.models.user import User

warehouse_bp = Blueprint("warehouse", __name__, url_prefix="/warehouse")


def warehouse_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.has_warehouse_access():
            flash("Доступ запрещён.", "error")
            return redirect(url_for("dashboard.index"))
        return f(*args, **kwargs)
    return login_required(decorated)


# ---------- ТОВАРЫ ----------

@warehouse_bp.route("/")
@warehouse_required
def index():
    search = request.args.get("q", "").strip()
    category_id = request.args.get("category", type=int)
    query = Item.query
    if search:
        query = query.filter(Item.name.ilike(f"%{search}%"))
    if category_id:
        query = query.filter_by(category_id=category_id)
    items = query.order_by(Item.name).all()
    categories = Category.query.order_by(Category.name).all()
    return render_template("warehouse/index.html", items=items, categories=categories, search=search)


@warehouse_bp.route("/item/add", methods=["GET", "POST"])
@warehouse_required
def add_item():
    categories = Category.query.order_by(Category.name).all()
    if request.method == "POST":
        item = Item(
            name=request.form["name"].strip(),
            article=request.form.get("article", "").strip() or None,
            category_id=request.form.get("category_id", type=int),
            unit=request.form.get("unit", "шт"),
            quantity=float(request.form.get("quantity", 0)),
            min_quantity=float(request.form.get("min_quantity", 0)),
            location=request.form.get("location", "").strip() or None,
            notes=request.form.get("notes", "").strip() or None,
        )
        db.session.add(item)
        db.session.commit()
        flash(f"Позиция «{item.name}» добавлена.", "success")
        return redirect(url_for("warehouse.index"))
    return render_template("warehouse/item_form.html", item=None, categories=categories)


@warehouse_bp.route("/item/<int:item_id>/edit", methods=["GET", "POST"])
@warehouse_required
def edit_item(item_id):
    item = Item.query.get_or_404(item_id)
    categories = Category.query.order_by(Category.name).all()
    if request.method == "POST":
        item.name = request.form["name"].strip()
        item.article = request.form.get("article", "").strip() or None
        item.category_id = request.form.get("category_id", type=int)
        item.unit = request.form.get("unit", "шт")
        item.quantity = float(request.form.get("quantity", 0))
        item.min_quantity = float(request.form.get("min_quantity", 0))
        item.location = request.form.get("location", "").strip() or None
        item.notes = request.form.get("notes", "").strip() or None
        item.updated_at = datetime.utcnow()
        db.session.commit()
        flash(f"Позиция «{item.name}» обновлена.", "success")
        return redirect(url_for("warehouse.index"))
    return render_template("warehouse/item_form.html", item=item, categories=categories)


@warehouse_bp.route("/item/<int:item_id>/delete", methods=["POST"])
@warehouse_required
def delete_item(item_id):
    item = Item.query.get_or_404(item_id)
    db.session.delete(item)
    db.session.commit()
    flash(f"Позиция «{item.name}» удалена.", "success")
    return redirect(url_for("warehouse.index"))


# ---------- ЗАКАЗЫ ----------

@warehouse_bp.route("/orders")
@warehouse_required
def orders():
    status_filter = request.args.get("status", "")
    query = Order.query
    if status_filter:
        query = query.filter_by(status=status_filter)
    all_orders = query.order_by(Order.created_at.desc()).all()
    return render_template("warehouse/orders.html", orders=all_orders, status_filter=status_filter)


@warehouse_bp.route("/orders/create", methods=["GET", "POST"])
@warehouse_required
def create_order():
    engineers = User.query.filter(User.role.in_(["engineer", "director"])).all()
    items = Item.query.order_by(Item.name).all()

    if request.method == "POST":
        last = Order.query.order_by(Order.id.desc()).first()
        next_id = (last.id + 1) if last else 1
        number = f"КМ-{next_id:04d}"

        order = Order(
            number=number,
            object_name=request.form["object_name"].strip(),
            status="new",
            notes=request.form.get("notes", "").strip() or None,
            created_by_id=current_user.id,
            assigned_to_id=request.form.get("assigned_to_id", type=int),
        )
        db.session.add(order)
        db.session.flush()

        item_ids = request.form.getlist("item_id[]")
        quantities = request.form.getlist("quantity[]")
        for item_id, qty in zip(item_ids, quantities):
            if item_id and qty:
                oi = OrderItem(
                    order_id=order.id,
                    item_id=int(item_id),
                    quantity=float(qty),
                )
                db.session.add(oi)

        db.session.commit()
        flash(f"Заказ {number} создан.", "success")
        return redirect(url_for("warehouse.orders"))

    return render_template("warehouse/order_form.html", engineers=engineers, items=items)


@warehouse_bp.route("/orders/<int:order_id>/status", methods=["POST"])
@warehouse_required
def update_order_status(order_id):
    order = Order.query.get_or_404(order_id)
    new_status = request.form.get("status")
    if new_status in Order.STATUS_CHOICES:
        order.status = new_status
        if new_status == "issued":
            order.issued_at = datetime.utcnow()
        db.session.commit()
        flash(f"Статус заказа {order.number} обновлён.", "success")
    return redirect(url_for("warehouse.orders"))


# ---------- EXCEL ЭКСПОРТ ----------

@warehouse_bp.route("/export/items")
@warehouse_required
def export_items():
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Склад"

    ws.merge_cells("A1:G1")
    ws["A1"] = "ООО ЧОО АБ Радонеж — Остатки склада"
    ws["A1"].font = Font(bold=True, size=14)
    ws["A1"].alignment = Alignment(horizontal="center")
    ws.append([])

    headers = ["№", "Наименование", "Артикул", "Категория", "Кол-во", "Ед.изм.", "Место"]
    ws.append(headers)
    hrow = ws.max_row
    for cell in ws[hrow]:
        cell.font = Font(bold=True, color="B98C50")
        cell.fill = PatternFill("solid", fgColor="1A1A1F")
        cell.alignment = Alignment(horizontal="center")

    for idx, item in enumerate(Item.query.order_by(Item.name).all(), 1):
        ws.append([
            idx, item.name, item.article or "—",
            item.category.name if item.category else "—",
            item.quantity, item.unit, item.location or "—",
        ])

    for col, width in zip("ABCDEFG", [5, 40, 15, 20, 10, 8, 20]):
        ws.column_dimensions[col].width = width

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    filename = f"sklad_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
    return send_file(buf, as_attachment=True, download_name=filename,
                     mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


@warehouse_bp.route("/export/order/<int:order_id>")
@warehouse_required
def export_order(order_id):
    import openpyxl
    from openpyxl.styles import Font, Alignment

    order = Order.query.get_or_404(order_id)
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = f"Заказ {order.number}"

    ws.merge_cells("A1:E1")
    ws["A1"] = f"Заказ {order.number} — {order.object_name}"
    ws["A1"].font = Font(bold=True, size=13)
    ws.append(["Инженер:", order.assignee.full_name if order.assignee else "—"])
    ws.append(["Статус:", order.status_label])
    ws.append(["Создан:", order.created_at.strftime("%d.%m.%Y %H:%M")])
    ws.append([])

    ws.append(["№", "Наименование", "Кол-во", "Ед.изм.", "Примечание"])
    for cell in ws[ws.max_row]:
        cell.font = Font(bold=True)

    for idx, oi in enumerate(order.items, 1):
        ws.append([idx, oi.item.name, oi.quantity, oi.item.unit, oi.notes or ""])

    for col, width in zip("ABCDE", [5, 40, 10, 8, 25]):
        ws.column_dimensions[col].width = width

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    filename = f"order_{order.number}_{datetime.now().strftime('%Y%m%d')}.xlsx"
    return send_file(buf, as_attachment=True, download_name=filename,
                     mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")